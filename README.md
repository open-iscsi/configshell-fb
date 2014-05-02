# ConfigShell

ConfigShell is a Python library that provides a framework for building
simple but nice CLI-based applications running both as single-command
tools and interactive shells providing a UNIX filesystem-like navigation
interface, as well as full autocompletion support and interactive inline help.

## Usage scenarios

ConfigShell can be used to write any CLI-based program, typically system
administration interfaces. The Linux Kernel's SCSI Target CLI, targetcli,
is written using ConfigShell (http://github.com/Datera/targetcli).

## Installation

ConfigShell is currently part of several Linux distributions, either under the
`configshell` name or `python-configshell`. In most cases, simply installing
the version packaged by your favorite Linux distribution is the best way to get
it running.

## Building from source

The packages are very easy to build and install from source as long as
you're familiar with your Linux Distribution's package manager:

1.  Clone the github repository for configshell using `git clone
    https://github.com/Datera/configshell.git`.

2.  Make sure build dependencies are installed. To build ConfigShell, you will need:

	* GNU Make.
	* python 2.6 or 2.7
	* A few python libraries: epydoc and pyparsing
	* A working LaTeX installation and ghostscript for building the
	  documentation, for example texlive-latex.
	* Your favorite distribution's package developement tools, like rpm for
	  Redhat-based systems or dpkg-dev and debhelper for Debian systems.

3.  From the cloned git repository, run `make deb` to generate a Debian
    package, or `make rpm` for a Redhat package.

4.  The newly built packages will be generated in the `dist/` directory.

5.  To cleanup the repository, use `make clean` or `make cleanall` which also
    removes `dist/*` files.

6.  To run the example shell from the source directory use `PYTHONPATH=. ./examples/myshell`

## Documentation

The ConfigShell packages do ship with a full API documentation in both HTML and PDF
formats, typically in `/usr/share/doc/python-configshell/doc`

Depending on your Linux distribution, the documentation might be shipped in a
separate package.

An other good source of information is the http://linux-iscsi.org wiki,
offering many resources such as (not necessarily up-to-date) copies of the
ConfigShell API Reference Guide (HTML at
http://linux-iscsi.org/Doc/configshell/html and PDF at
http://linux-iscsi.org/Doc/configshell/configshell-API-reference.pdf).
The Targetcli User's Guide at http://linux-iscsi.org/wiki/targetcli might also
provide interesting information as an example program written using
ConfigShell.

A simple example called `myshell` is included in the source tree and should be
installed on your system in a location like `/usr/share/doc/python-configshell/`.

## Author

ConfigShell was developed by Datera, Inc.
http://www.datera.io

The original author and current maintainer is
Jerome Martin, at <mailto:jxm@netiant.com>
