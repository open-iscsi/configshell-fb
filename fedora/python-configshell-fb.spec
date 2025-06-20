%global upstream_name configshell-fb
%global pkg_name configshell

Name:           python-%{pkg_name}
Version:        1.1.29
Release:        %autorelease
Summary:        A framework to implement simple but nice CLIs
# Note: This is the fb version of configshell

License:        Apache-2.0
URL:            http://github.com/open-iscsi/%{upstream_name}
Source0:        %{pypi_source %{upstream_name}}

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-pip
BuildRequires:  hatch
BuildRequires:  python3-hatchling
BuildRequires:  python3-hatch-vcs

%global _description %{expand:
configshell-fb is a Python library that provides a framework to implement simple
but nice CLI-based applications.
}

%description
%{_description}

%package -n python3-%{pkg_name}
Summary:        %{summary}
%{?python_provide:%python_provide python3-%{pkg_name}}

Requires:       python3-pyparsing >= 2.4.7

%description -n python3-%{pkg_name}
%{_description}

%prep
%autosetup -n %{upstream_name}-%{version}
rm -rf %{upstream_name}.egg-info

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files configshell configshell_fb

%files -n python3-%{pkg_name} -f %{pyproject_files}
%license COPYING
%doc README.md

%changelog
%autochangelog
