# Fedora RPM packaging

This directory contains Fedora-style packaging for `geoipsets`.

For SIP abuse detection with Suricata, IFB mirroring, and API-backed reputation
checks, see `docs/sip-ifb-reputation.md`.

The spec follows Fedora Python packaging practice by using the pyproject RPM
macros against the upstream `python/` subdirectory:

- `%pyproject_buildrequires -d python`
- `%pyproject_wheel -d python`
- `%pyproject_install`
- `%pyproject_save_files geoipsets`

The repository currently has `python/geoipsets/VERSION` set to `2.4.0`, but the
fork has no release tags. The spec therefore packages the current Git commit as
a snapshot release:

```text
2.4.0-0.10.20260506gitfdc367f
```

When an upstream release tag exists, update `Source0`, remove the commit
snapshot globals, and switch `Release` to `1%{?dist}`.

## Packaged files

- `/etc/geoipsets.conf`: default configuration, installed as `%config(noreplace)`
- `/etc/geoipsets.blocklist`: manual public proxy/VPN/abuse endpoint blocklist
- `/etc/geoipsets.blocklist-feeds.conf`: dynamic abuse blocklist feed config
- `/etc/geoipsets.blocklist.d`: local blocklist drop-in directory
- `/usr/lib/systemd/system/update-geoipsets.service`: hardened one-shot updater
- `/usr/lib/systemd/system/update-geoipsets.timer`: weekly refresh timer
- `/usr/libexec/geoipsets/refresh-ipset`: reloads generated ipset files
- `/usr/libexec/geoipsets/fetch-blocklists`: downloads dynamic blocklist feeds
- `/usr/libexec/geoipsets/refresh-blocklist`: reloads manual and dynamic blocklist ipsets
- `/usr/sbin/geoipsets-ifbctl`: optional SIP IFB mirror helper for Suricata
- `/usr/lib/tmpfiles.d/geoipsets.conf`: creates `/var/lib/geoipsets`
- `/var/lib/geoipsets`: generated provider output tree

The packaged default uses DB-IP, nftables output, and both IPv4 and IPv6. MaxMind
is supported by the application but requires users to add credentials in
`/etc/geoipsets.conf`.

After generating files, `update-geoipsets.service` runs the ipset refresh helper.
The helper flushes any existing generated sets and restores updated entries from
`/var/lib/geoipsets/dbip/ipset` using native set names such as `CA.ipv4` and
`CA.ipv6`. For older Shorewall configurations that expect names such as
`ipv4_CA` and `ipv6_CA`, run `/usr/libexec/geoipsets/refresh-ipset --legacy`.
To make the timer use legacy names, add a systemd drop-in that clears and
replaces `ExecStartPost` with the same command plus `--legacy`.

Manual proxy, VPN, and abuse endpoints can be added to `/etc/geoipsets.blocklist`
or `/etc/geoipsets.blocklist.d/*.list` with one IP address or CIDR network per
line. Comments with `#` are allowed. Dynamic feeds are downloaded into
`/var/lib/geoipsets/blocklists/feeds/*.list`. Learned local lists can live under
`/var/lib/geoipsets/blocklists/*.list`. The refresh helper creates or updates
`blocked_ipv4` and `blocked_ipv6` with a temporary-set swap, so rules can
reference those sets while entries are updated.
For example:

```text
45.146.55.104
203.0.113.0/24
2001:db8:bad::/48
```

Dynamic abuse feeds are configured in `/etc/geoipsets.blocklist-feeds.conf`
using foomuri-style `iplist` entries:

```text
iplist {
    @abuseipdb https://raw.githubusercontent.com/borestad/blocklist-abuseipdb/main/abuseipdb-s100-14d.ipv4
    @et https://rules.emergingthreats.net/fwrules/emerging-Block-IPs.txt
    @spamhausdropv6 https://www.spamhaus.org/drop/dropv6.txt
}
```

Only put block feeds in this file. Country allowlists such as `@ipv4_CA` and
`@ipv4_US` belong in geo policy sets, not in the blocklist feed config.

If you override the service for legacy Shorewall country set names, keep the
blocklist refresh in the override too:

```ini
[Service]
ExecStartPost=
ExecStartPost=/usr/libexec/geoipsets/refresh-ipset --legacy
ExecStartPost=/usr/libexec/geoipsets/fetch-blocklists
ExecStartPost=/usr/libexec/geoipsets/refresh-blocklist
```

`output-dir` is the parent directory used by the application. The Python code
appends `geoipsets/` internally, so the packaged `output-dir=/var/lib` writes
generated files under `/var/lib/geoipsets`.

## Build locally

Install the Fedora RPM build tools:

```bash
sudo dnf install rpm-build rpmdevtools python3-devel pyproject-rpm-macros systemd-rpm-macros
```

From the repository root:

```bash
./rpm/build-rpm.sh
```

The script creates a source archive from the current checkout and runs
`rpmbuild -ba` with `_sourcedir` pointed at that archive.
