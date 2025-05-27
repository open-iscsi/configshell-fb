%global pypi_name configshell-fb

Name:           python-%{pypi_name}
Version:        1.1.29
Release:        1%{?dist}
Summary:        A framework to implement simple but nice CLIs

License:        Apache-2.0
URL:            http://github.com/open-iscsi/configshell-fb
Source0:        %{pypi_source}

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-pip
BuildRequires:  python3-hatchling
BuildRequires:  python3-hatch-vcs

%description
configshell-fb is a Python library that provides a framework to implement simple
but nice CLI-based applications.

%package -n python3-%{pypi_name}
Summary:        %{summary}
%{?python_provide:%python_provide python3-%{pypi_name}}

Requires:       python3-pyparsing >= 2.4.7

%description -n python3-%{pypi_name}
configshell-fb is a Python library that provides a framework to implement simple
but nice CLI-based applications.

%prep
%autosetup -n %{pypi_name}-%{version}
rm -rf %{pypi_name}.egg-info

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files configshell configshell_fb.py

%files -n python3-%{pypi_name} -f %{pyproject_files}
%license COPYING
%doc README.md

%changelog
* Thu May 23 2024 Packit <packit> - 1.1.29-1
- Initial package for Fedora
