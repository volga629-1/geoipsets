%global commit fdc367fade27b946f7694423f61add42359e031b
%global shortcommit %(c=%{commit}; echo ${c:0:7})
%global snapdate 20260506

Name:           geoipsets
Version:        2.4.0
Release:        0.32.%{snapdate}git%{shortcommit}%{?dist}
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
Source11:       geoipsets-update-all
Source12:       geoipsets-reputation.env
Source13:       geoipsets-reputation-worker
Source14:       geoipsets-reputation-worker.service
Source15:       geoipsets-local-sip.rules
Source16:       geoipsets-provision-sip-suricata

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3dist(pytest)
BuildRequires:  systemd-rpm-macros

Requires:       ipset
Requires:       curl
Requires:       conntrack-tools
Requires:       iproute
Requires:       iproute-tc
Requires:       kmod
Requires:       python3
Requires:       systemd
Recommends:     suricata

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
install -Dpm 0755 %{SOURCE11} %{buildroot}%{_libexecdir}/geoipsets/update-all
install -Dpm 0640 %{SOURCE12} %{buildroot}%{_sysconfdir}/geoipsets-reputation.env
install -Dpm 0755 %{SOURCE13} %{buildroot}%{_libexecdir}/geoipsets/reputation-worker
install -Dpm 0644 %{SOURCE14} %{buildroot}%{_unitdir}/geoipsets-reputation-worker.service
install -Dpm 0644 %{SOURCE15} %{buildroot}%{_datadir}/geoipsets/suricata/local-sip.rules
install -Dpm 0755 %{SOURCE16} %{buildroot}%{_sbindir}/geoipsets-provision-sip-suricata
install -dpm 0755 %{buildroot}%{_sysconfdir}/geoipsets.blocklist.d
install -dpm 0755 %{buildroot}%{_sharedstatedir}/geoipsets
install -dpm 0755 %{buildroot}%{_sharedstatedir}/geoipsets/blocklists
install -dpm 0755 %{buildroot}%{_sharedstatedir}/geoipsets/blocklists/feeds
install -dpm 0755 %{buildroot}%{_sharedstatedir}/geoipsets/reputation

%check
%pyproject_check_import
pushd python
%{py3_test_envvars} %{python3} -m pytest
popd

%post
%systemd_post update-geoipsets.service update-geoipsets.timer geoipsets-reputation-worker.service
%tmpfiles_create geoipsets.conf
if [ -f %{_sysconfdir}/geoipsets.blocklist-feeds.conf.rpmnew ]; then
    echo ">>> [RPM] %{_sysconfdir}/geoipsets.blocklist-feeds.conf.rpmnew contains updated default abuse feeds; merge or replace the existing config to enable them."
fi

%preun
%systemd_preun update-geoipsets.service update-geoipsets.timer geoipsets-reputation-worker.service

%postun
%systemd_postun_with_restart update-geoipsets.service geoipsets-reputation-worker.service
%systemd_postun update-geoipsets.timer

%files -f %{pyproject_files}
%license LICENSE
%doc python/README.md
%doc docs/sip-ifb-reputation.md
%config(noreplace) %{_sysconfdir}/geoipsets.conf
%config(noreplace) %{_sysconfdir}/geoipsets.blocklist
%config(noreplace) %{_sysconfdir}/geoipsets.blocklist-feeds.conf
%config(noreplace) %attr(0640,root,root) %{_sysconfdir}/geoipsets-reputation.env
%dir %{_sysconfdir}/geoipsets.blocklist.d
%{_bindir}/geoipsets
%{_sbindir}/geoipsets-ifbctl
%{_sbindir}/geoipsets-provision-sip-suricata
%{_libexecdir}/geoipsets/refresh-ipset
%{_libexecdir}/geoipsets/refresh-blocklist
%{_libexecdir}/geoipsets/fetch-blocklists
%{_libexecdir}/geoipsets/update-all
%{_libexecdir}/geoipsets/reputation-worker
%{_unitdir}/update-geoipsets.service
%{_unitdir}/update-geoipsets.timer
%{_unitdir}/geoipsets-reputation-worker.service
%{_tmpfilesdir}/geoipsets.conf
%dir %{_datadir}/geoipsets
%dir %{_datadir}/geoipsets/suricata
%{_datadir}/geoipsets/suricata/local-sip.rules
%dir %{_sharedstatedir}/geoipsets
%dir %{_sharedstatedir}/geoipsets/blocklists
%dir %{_sharedstatedir}/geoipsets/blocklists/feeds
%dir %{_sharedstatedir}/geoipsets/reputation

%changelog
* Mon Jul 27 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.32.20260506gitfdc367f
- Detect TUFAN scanner variants and SIP SQL injection header probes.

* Sun Jul 26 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.31.20260506gitfdc367f
- Detect TUFAN SDP call markers and log already-blocked reputation events.

* Sun Jul 26 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.30.20260506gitfdc367f
- Add structured reputation worker journal logs and JSONL decision collector.

* Sun Jul 26 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.29.20260506gitfdc367f
- Detect SIP path traversal URI probes.

* Sun Jul 26 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.28.20260506gitfdc367f
- Detect TUFAN scanner and SIP file URI probes.

* Sun Jul 26 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.27.20260506gitfdc367f
- Derive Suricata local SIP rule path from update.yaml during provisioning.

* Sat Jul 25 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.26.20260506gitfdc367f
- Add DShield feed parser and SIP Suricata provisioning helper.

* Sat Jul 25 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.25.20260506gitfdc367f
- Broaden long numeric SIP INVITE probe detection to numeric Contact users.

* Fri Jul 24 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.24.20260506gitfdc367f
- Detect long numeric SIP INVITE probes and repeated INVITE sources.

* Sat Jul 11 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.23.20260506gitfdc367f
- Treat learned SIP offenders as a local blocklist before reputation API lookup.

* Sun Jul 05 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.22.20260506gitfdc367f
- Check reputation immediately for SIP INVITE and REGISTER parser events.

* Sun Jul 05 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.21.20260506gitfdc367f
- Trigger reputation checks for generic inbound SIP INVITE traffic.

* Sun Jul 05 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.20.20260506gitfdc367f
- Allow the reputation worker to read Suricata EVE logs via the suricata group.

* Sun Jul 05 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.19.20260506gitfdc367f
- Add local Suricata SIP reputation worker with IPQS and AbuseIPDB checks.

* Sun Jul 05 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.18.20260506gitfdc367f
- Support dummy-backed SIP mirror interfaces for local Suricata capture.

* Sun Jul 05 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.17.20260506gitfdc367f
- Clean stale temporary ipsets left by interrupted or failed refreshes.

* Sun Jul 05 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.16.20260506gitfdc367f
- Auto-size country ipset restores with headroom and support COUNTRY_MAXELEM.

* Sun Jul 05 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.15.20260506gitfdc367f
- Auto-size blocklist ipsets with headroom and support BLOCKLIST_MAXELEM.

* Sun Jul 05 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.14.20260506gitfdc367f
- Show qdisc and packet counters in geoipsets-ifbctl status.

* Sun Jul 05 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.13.20260506gitfdc367f
- Continue refreshing abuse blocklists when the country database download fails.
- Notify operators when updated feed defaults are installed as rpmnew.

* Sun Jul 05 2026 Telbit dev <info@telbit.dev> - 2.4.0-0.12.20260506gitfdc367f
- Enable the default public abuse blocklist feed catalog.

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
