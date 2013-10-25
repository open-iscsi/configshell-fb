configshell-fb
==============

A Python library for building configuration shells
--------------------------------------------------
configshell-fb is a Python library that provides a framework
for building simple but nice CLI-based applications.

This runs with Python 2 and 2to3 is run by setup.py to run on Python 3.

configshell-fb development
--------------------------
configshell-fb is licensed under the Apache 2.0 license. Contributions are welcome.

Since configshell-fb is used most often with targetcli-fb, the
targetcli-fb mailing should be used for configshell-fb discussion.

 * Mailing list: [targetcli-fb-devel](https://lists.fedorahosted.org/mailman/listinfo/targetcli-fb-devel)
 * Source repo: [GitHub](https://github.com/agrover/configshell-fb)
 * Bugs: [GitHub](https://github.com/agrover/configshell-fb/issues) or [Trac](https://fedorahosted.org/targetcli-fb/)
 * Tarballs: [fedorahosted](https://fedorahosted.org/releases/t/a/targetcli-fb/)

In-repo packaging
-----------------
Packaging scripts for RPM and DEB are included, but these are to make end-user
custom packaging easier -- distributions tend to maintain their own packaging
scripts separately. If you run into issues with packaging, start with opening
a bug on your distro's bug reporting system.

Some people do use these scripts, so we want to keep them around. Fixes for
any breakage you encounter are welcome.

"fb" -- "free branch"
---------------------

configshell-fb is a fork of the "configshell" code written by
RisingTide Systems. The "-fb" differentiates between the original and
this version. Please ensure to use either all "fb" versions of the
targetcli components -- targetcli, rtslib, and configshell, or stick
with all non-fb versions, since they are no longer strictly
compatible.
