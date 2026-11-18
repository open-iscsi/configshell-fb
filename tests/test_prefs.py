import errno
import os
import stat
import struct
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from configshell.prefs import Prefs

ACCESS_ACL = 'system.posix_acl_access'
DEFAULT_ACL = 'system.posix_acl_default'


class PrefsSaveTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / 'prefs.bin'
        borg_state = patch.object(Prefs, '_Prefs__borg_state', {'_prefs': {}})
        borg_state.start()
        self.addCleanup(borg_state.stop)
        self.prefs = Prefs(self.path)
        self.prefs['example'] = 'updated'

    def set_acl(self, path, name):
        if not hasattr(os, 'setxattr'):
            self.skipTest('POSIX ACL xattrs are unavailable')
        # Linux POSIX ACL xattr version 2 with a named user and a mask.
        acl = struct.pack('<I', 2)
        named_uid = os.geteuid()
        for tag, permissions, qualifier in (
            (1, 7, 0xFFFFFFFF),  # Owner
            (2, 4, named_uid),
            (4, 0, 0xFFFFFFFF),  # Owning group
            (16, 4, 0xFFFFFFFF),  # Mask
            (32, 0, 0xFFFFFFFF),  # Other
        ):
            acl += struct.pack('<HHI', tag, permissions, qualifier)
        try:
            os.setxattr(path, name, acl)
        except OSError as error:
            if error.errno in {errno.ENOSYS, errno.ENOTSUP}:
                self.skipTest('The temporary filesystem does not support POSIX ACLs')
            raise

    def test_save_syncs_parent_after_rename(self):
        synced = []
        fsync = os.fsync

        def record_sync(fd):
            synced.append(os.fstat(fd))
            if stat.S_ISDIR(synced[-1].st_mode):
                self.assertTrue(self.path.is_file())
            else:
                self.assertFalse(self.path.exists())
            fsync(fd)

        with patch.object(os, 'fsync', side_effect=record_sync):
            self.prefs.save()

        file_stat, dir_stat = synced
        self.assertTrue(os.path.samestat(file_stat, self.path.stat()))
        self.assertTrue(os.path.samestat(dir_stat, self.path.parent.stat()))

    def test_save_preserves_existing_access_acl(self):
        self.path.touch()
        self.set_acl(self.path, ACCESS_ACL)
        expected = os.getxattr(self.path, ACCESS_ACL)

        self.prefs.save()

        self.assertEqual(os.getxattr(self.path, ACCESS_ACL), expected)

    def test_save_does_not_add_access_acl_to_existing_file(self):
        self.path.touch(mode=0o640)
        self.set_acl(self.path.parent, DEFAULT_ACL)
        probe = self.path.with_name('acl-probe')
        probe.touch(mode=0o640)
        self.assertTrue(os.getxattr(probe, ACCESS_ACL))

        self.prefs.save()

        self.assertNotIn(ACCESS_ACL, os.listxattr(self.path))

    def test_existing_file_replacement_starts_private(self):
        self.path.touch(mode=0o644)
        self.path.chmod(0o644)
        initial_modes = []
        original_open = os.open

        def record_mode(path, flags, *args, **kwargs):
            fd = original_open(path, flags, *args, **kwargs)
            if flags & os.O_CREAT:
                initial_modes.append(stat.S_IMODE(os.fstat(fd).st_mode))
            return fd

        old_umask = os.umask(0o022)
        try:
            with patch.object(os, 'open', side_effect=record_mode):
                self.prefs.save()
        finally:
            os.umask(old_umask)

        self.assertEqual(initial_modes, [0o600])
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o644)

    def test_save_rejects_read_only_file(self):
        original = b'original preferences'
        self.path.write_bytes(original)
        self.path.chmod(0o444)
        if os.access(self.path, os.W_OK):
            self.skipTest('Current user can write to mode 0444 files')

        with self.assertRaises(PermissionError):
            self.prefs.save()

        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o444)


if __name__ == '__main__':
    unittest.main()
