# Copyright 2011, Red Hat
# The Fedora package is built from this spec file. Packit copies it to
# Fedora dist-git with every release (propose_downstream in .packit.yaml),
# so change the packaging here rather than in dist-git.

Name:           python-configshell
License:        Apache-2.0
Summary:        A framework to implement simple but nice CLIs
Epoch:          1
Version:        2.0.3
Release:        %autorelease
URL:            https://github.com/open-iscsi/configshell-fb
Source:         %{pypi_source configshell_fb}
BuildArch:      noarch

BuildRequires:  python3-devel

%global _description\
A framework to implement simple but nice configuration-oriented\
command-line interfaces.

%description %_description

%package -n python3-configshell
Summary:        A framework to implement simple but nice CLIs

%description -n python3-configshell %_description

%prep
%autosetup -n configshell_fb-%{version}

%generate_buildrequires
%pyproject_buildrequires

%build
%pyproject_wheel

%install
%pyproject_install
# configshell_fb is a deprecated alias of configshell
%pyproject_save_files -l configshell configshell_fb

%check
%pyproject_check_import

%files -n python3-configshell -f %{pyproject_files}
%doc README.md

%changelog
%autochangelog
