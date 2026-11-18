'''
This file is part of ConfigShell.
Copyright (c) 2011-2013 by Datera, Inc

Licensed under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.
'''

import errno
import os
import pickle
import secrets
import stat
from contextlib import suppress
from pathlib import Path

_ACCESS_ACL = 'system.posix_acl_access'


def _create_tempfile(path, mode):
    '''
    Creates an empty temporary file in the same directory as path.
    @param path: The file the temporary file will later replace.
    @type path: Path
    @param mode: The creation mode passed to os.open().
    @return: The open file descriptor and the temporary file's path.
    @rtype: (int, Path)
    '''
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    # try to find a free filename, in case one already exists
    for _ in range(100):
        tmp = path.with_name(f'.{path.name}.{secrets.token_hex(4)}')
        with suppress(FileExistsError):
            return os.open(tmp, flags, mode), tmp
    raise FileExistsError(f'Could not create a temporary file next to {path}')


def _get_access_acl(fd):
    if not hasattr(os, 'getxattr'):
        return None
    try:
        return os.getxattr(fd, _ACCESS_ACL)
    except OSError as error:
        if error.errno not in (errno.ENODATA, errno.ENOTSUP):
            raise
        return None


def _restore_permissions(fd, original, acl):
    # Keep the original ownership where permitted.
    with suppress(PermissionError):
        os.fchown(fd, original.st_uid, original.st_gid)

    # Clear any inherited ACL before widening permissions.
    if acl is not None:
        os.setxattr(fd, _ACCESS_ACL, acl)
    elif hasattr(os, 'removexattr'):
        try:
            os.removexattr(fd, _ACCESS_ACL)
        except OSError as error:
            if error.errno not in (errno.ENODATA, errno.ENOTSUP):
                raise
    os.fchmod(fd, stat.S_IMODE(original.st_mode))


class Prefs:
    '''
    This is a preferences backend object used to:
        - Hold the ConfigShell preferences
        - Handle persistent storage and retrieval of these preferences
        - Share the preferences between the ConfigShell and ConfigNode objects

    As it is inherently destined to be shared between objects, this is a Borg.
    '''
    _prefs = {}
    filename = None
    autosave = False
    __borg_state = {}

    def __init__(self, filename=None):
        '''
        Instanciates the ConfigShell preferences object.
        @param filename: File to store the preferencces to.
        @type filename: str
        '''
        self.__dict__ = self.__borg_state
        if filename is not None:
            self.filename = filename

    def __getitem__(self, key):
        '''
        Proxies dict-like references to prefs.
        One specific behavior, though, is that if the key does not exists,
        we will return None instead of raising an exception.
        @param key: The preferences dictionnary key to get.
        @type key: any valid dict key
        @return: The key value
        @rtype: n/a
        '''
        if key in self._prefs:
            return self._prefs[key]
        else:
            return None

    def __setitem__(self, key, value):
        '''
        Proxies dict-like references to prefs.
        @param key: The preferences dictionnary key to set.
        @type key: any valid dict key
        '''
        self._prefs[key] = value
        if self.autosave:
            self.save()

    def __contains__(self, key):
        '''
        Do the preferences contain key ?
        @param key: The preferences dictionnary key to check.
        @type key: any valid dict key
        '''
        return key in self._prefs

    def __delitem__(self, key):
        '''
        Deletes a preference key.
        @param key: The preference to delete.
        @type key: any valid dict key
        '''
        del self._prefs[key]
        if self.autosave:
            self.save()

    def __iter__(self):
        '''
        Generic iterator for the preferences.
        '''
        return self._prefs.__iter__()

    # Public methods

    def keys(self):
        '''
        @return: Returns the list of keys in preferences.
        @rtype: list
        '''
        return self._prefs.keys()

    def items(self):
        '''
        @return: Returns the list of items in preferences.
        @rtype: list of (key, value) tuples
        '''
        return self._prefs.items()

    def iteritems(self):
        '''
        @return: Iterates on the items in preferences.
        @rtype: yields items that are (key, value) pairs
        '''
        return self._prefs.items()

    def save(self, filename=None):
        '''
        Saves the preferences to disk. If filename is not specified,
        use the default one if it is set, else do nothing.
        @param filename: Optional alternate file to use.
        @type filename: str
        '''
        if filename is None:
            filename = self.filename

        if filename is not None:
            path = Path(filename).resolve()
            try:
                original_fd = os.open(path, os.O_WRONLY | os.O_NONBLOCK)
            except FileNotFoundError:
                current = None
            else:
                try:
                    current = os.fstat(original_fd)
                    acl = _get_access_acl(original_fd)
                finally:
                    os.close(original_fd)
            fd, tmp = _create_tempfile(path, 0o666 if current is None else 0o600)
            try:
                with os.fdopen(fd, 'wb') as fsock:
                    pickle.dump(self._prefs, fsock, 2)
                    fsock.flush()
                    if current is not None:
                        _restore_permissions(fd, current, acl)
                    os.fsync(fd)
                tmp.replace(path)
            except BaseException:
                tmp.unlink(missing_ok=True)
                raise

            # Persist the directory entry created by the rename.
            dir_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)

    def load(self, filename=None):
        '''
        Loads the preferences from file. Use either the supplied filename,
        or the default one if set. Else, do nothing.
        '''
        if filename is None:
            filename = self.filename

        if filename is not None and Path(filename).exists():
            path = Path(filename)
            with path.open('rb') as fsock:
                self._prefs = pickle.load(fsock)  # noqa S301 TODO
