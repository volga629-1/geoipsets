%global commit fdc367fade27b946f7694423f61add42359e031b
%global shortcommit %(c=%{commit}; echo ${c:0:7})
%global snapdate 20260506

Name:           geoipsets
Version:        2.4.0
Release:        0.11.%{snapdate}git%{shortcommit}%{?dist}
Summary:        Build country-specific IP sets for ipset and nftables

License:        GPL-3.0-only
URL:            https://github.com/volga629-1/geoipsets
Source0:        %{url}/archive/%{commit}/%{name}-%{shortcommit}.tar.gz
Source1:        geoipsets.conf
Source2:        update-geoipsets.service
Source3:        update-geoipsets.timer
Source4:        geoipsets.tmpfiles
Source5:        geoipsets-refresh-ipset
Source6:        geoipsets.blocklist
Source7:        geoipsets-refresh-blocklist
Source8:        geoipsets.blocklist-feeds.conf
Source9:        geoipsets-fetch-blocklists
Source10:       geoipsets-ifbctl

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3dist(pytest)
BuildRequires:  systemd-rpm-macros

Requires:       ipset
Requires:       curl
Requires:       iproute
Requires:       iproute-tc
Requires:       kmod
Requires:       systemd

%description
geoipsets downloads country IP allocation data and generates files suitable for
ipset/iptables and nftables. The package includes a default configuration and
a systemd timer for periodic refreshes.

%prep
%autosetup -n %{name}-%{commit}
# Fedora build roots might not provide the unversioned "python" command.
sed -i "s|'python'|'%{python3}'|g" python/tests/config_test.py

%generate_buildrequires
%pyproject_buildrequires -d python

%build
%pyproject_wheel -d python

%install
%pyproject_install
%pyproject_save_files geoipsets

install -Dpm 0644 %{SOURCE1} %{buildroot}%{_sysconfdir}/geoipsets.conf
install -Dpm 0644 %{SOURCE2} %{buildroot}%{_unitdir}/update-geoipsets.service
install -Dpm 0644 %{SOURCE3} %{buildroot}%{_unitdir}/update-geoipsets.timer
install -Dpm 0644 %{SOURCE4} %{buildroot}%{_tmpfilesdir}/geoipsets.conf
install -Dpm 0755 %{SOURCE5} %{buildroot}%{_libexecdir}/geoipsets/refresh-ipset
install -Dpm 0644 %{SOURCE6} %{buildroot}%{_sysconfdir}/geoipsets.blocklist
install -Dpm 0755 %{SOURCE7} %{buildroot}%{_libexecdir}/geoipsets/refresh-blocklist
install -Dpm 0644 %{SOURCE8} %{buildroot}%{_sysconfdir}/geoipsets.blocklist-feeds.conf
install -Dpm 0755 %{SOURCE9} %{buildroot}%{_libexecdir}/geoipsets/fetch-blocklists
install -Dpm 0755 %{SOURCE10} %{buildroot}%{_sbindir}/geoipsets-ifbctl
install -dpm 0755 %{buildroot}%{_sysconfdir}/geoipsets.blocklist.d
install -dpm 0755 %{buildroot}%{_sharedstatedir}/geoipsets
install -dpm 0755 %{buildroot}%{_sharedstatedir}/geoipsets/blocklists
install -dpm 0755 %{buildroot}%{_sharedstatedir}/geoipsets/blocklists/feeds

%check
%pyproject_check_import
pushd python
%{py3_test_envvars} %{python3} -m pytest
popd

%post
%systemd_post update-geoipsets.service update-geoipsets.timer
%tmpfiles_create geoipsets.conf

%preun
%systemd_preun update-geoipsets.service update-geoipsets.timer

%postun
%systemd_postun_with_restart update-geoipsets.service
%systemd_postun update-geoipsets.timer

%files -f %{pyproject_files}
%license LICENSE
%doc python/README.md
%config(noreplace) %{_sysconfdir}/geoipsets.conf
%config(noreplace) %{_sysconfdir}/geoipsets.blocklist
%config(noreplace) %{_sysconfdir}/geoipsets.blocklist-feeds.conf
%dir %{_sysconfdir}/geoipsets.blocklist.d
%{_bindir}/geoipsets
%{_sbindir}/geoipsets-ifbctl
%{_libexecdir}/geoipsets/refresh-ipset
%{_libexecdir}/geoipsets/refresh-blocklist
%{_libexecdir}/geoipsets/fetch-blocklists
%{_unitdir}/update-geoipsets.service
%{_unitdir}/update-geoipsets.timer
%{_tmpfilesdir}/geoipsets.conf
%dir %{_sharedstatedir}/geoipsets
%dir %{_sharedstatedir}/geoipsets/blocklists
%dir %{_sharedstatedir}/geoipsets/blocklists/feeds

%changelog
* Sun Jul 05 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.11.20260506gitfdc367f
- Reset IFB mirror filters on geoipsets-ifbctl start and add restart command.

* Sun Jul 05 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.10.20260506gitfdc367f
- Add optional geoipsets-ifbctl helper for SIP IFB mirroring.

* Sun Jul 05 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.9.20260506gitfdc367f
- Add dynamic abuse blocklist feed fetching and loading.

* Sat Jul 04 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.8.20260506gitfdc367f
- Add manual public proxy/VPN abuse blocklist ipsets.

* Sun Jun 28 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.7.20260506gitfdc367f
- Refresh existing ipsets via temporary sets and swap to apply generated maxelem.

* Sun Jun 28 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.6.20260506gitfdc367f
- Strip entry comments when refreshing existing ipsets without comment support.

* Sun Jun 28 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.5.20260506gitfdc367f
- Avoid create statements when refreshing existing ipsets.

* Sun Jun 28 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.4.20260506gitfdc367f
- Make Shorewall-compatible ipset naming optional with refresh-ipset --legacy.

* Sun Jun 28 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.3.20260506gitfdc367f
- Restore ipset entries with Shorewall-compatible ipv4_CC and ipv6_CC names.

* Sun Jun 28 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.2.20260506gitfdc367f
- Add ipset refresh helper and run it after geoipsets updates.
- Require ipset for runtime refresh support.

* Wed May 06 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.1.20260506gitfdc367f
- Initial Fedora-style RPM package for the geoipsets Git snapshot.
