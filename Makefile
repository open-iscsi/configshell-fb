# This file is part of ConfigShell Community Edition.
# Copyright (c) 2011 by RisingTide Systems LLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, version 3 (AGPLv3).
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

NAME = configshell
LIB = /usr/share
DOC = ${LIB}/doc/
SETUP = ./setup.py
GENDOC = ./bin/gendoc
RPMVERSION = $$(grep Version: redhat/python-configshell.spec | awk '{print $$2}')
GIT_BRANCH = $$(git branch | grep \* | tr -d \*)

all: usage
usage:
	@echo "Usage:"
	@echo "  make deb         - Builds debian packages."
	@echo "  make rpm         - Builds redhat packages."
	@echo "  make clean       - Cleanup the local repository"
	@echo "  make cleanall    - Cleanup the local repository and packages"
	@echo "Developer targets:"
	@echo "  make doc         - Generate the documentation"
	@echo "  make sdist       - Build the source tarball"
	@echo "  make bdist       - Build the installable tarball"
	@echo "  make install     - Install configshell"
	@echo "  make installdocs - Install the documentation"

install:
	${SETUP} install

doc:
	${GENDOC}

installdocs: doc
	@test -e ${DOC} || \
	    echo "Could not find ${DOC}; check the makefile variables."
	@test -e ${DOC}
	cp -r doc/* ${DOC}/${NAME}/

clean:
	rm -fv configshell/*.pyc configshell/*.html
	rm -frv doc doc/*.pdf doc/html doc/pdf doc/*.html
	rm -frv configshell.egg-info MANIFEST build
	rm -frv pdf html
	rm -frv debian/tmp
	rm -fv build-stamp
	rm -fv dpkg-buildpackage.log dpkg-buildpackage.version
	rm -frv *.rpm
	rm -fv debian/files debian/*.log debian/*.substvars
	rm -frv debian/configshell-doc/ debian/python2.5-configshell/
	rm -frv debian/python2.6-configshell/ debian/python-configshell/
	rm -frv results
	rm -fv redhat/*.spec *.spec redhat/sed* sed*
	rm -frv configshell-*
	./bin/gen_changelog_cleanup
	@echo "Finished cleanup."

cleanall: clean
	rm -frv dist

deb: doc
	./bin/gen_changelog
	dpkg-buildpackage -rfakeroot | tee dpkg-buildpackage.log
	./bin/gen_changelog_cleanup
	grep "source version" dpkg-buildpackage.log | awk '{print $$4}' > dpkg-buildpackage.version
	@test -e dist || mkdir dist
	mv ../${NAME}_$$(cat dpkg-buildpackage.version).dsc dist
	mv ../${NAME}_$$(cat dpkg-buildpackage.version)_*.changes dist
	mv ../${NAME}_$$(cat dpkg-buildpackage.version).tar.gz dist
	mv ../*${NAME}*$$(cat dpkg-buildpackage.version)*.deb dist
	./bin/gen_changelog_cleanup

rpm: doc
	./bin/gen_changelog
	@echo Building RPM version ${RPMVERSION}
	mkdir -p ~/rpmbuild/SOURCES/
	mkdir -p build
	git archive $(GIT_BRANCH) --prefix configshell/ > build/configshell.tar
	cd build; tar mxf configshell.tar; rm configshell.tar
	cp configshell/__init__.py build/configshell/configshell
	cp -r doc build/configshell/
	mv build/configshell configshell-${RPMVERSION}
	tar zcf ~/rpmbuild/SOURCES/configshell-${RPMVERSION}.tar.gz configshell-${RPMVERSION}
	rm -fr configshell-${RPMVERSION}
	rpmbuild -ba redhat/*.spec
	@test -e dist || mkdir dist
	mv ~/rpmbuild/SRPMS/python-configshell-${RPMVERSION}*.src.rpm dist/
	mv ~/rpmbuild/RPMS/noarch/python-configshell-${RPMVERSION}*.rpm dist/
	mv ~/rpmbuild/RPMS/noarch/python-configshell-doc-${RPMVERSION}*.rpm dist/
	./bin/gen_changelog_cleanup

sdist: clean doc
	${SETUP} sdist

bdist: clean doc
	${SETUP} bdist

