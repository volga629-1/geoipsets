# Fedora RPM packaging

This directory contains Fedora-style packaging for `geoipsets`.

For SIP abuse detection with Suricata, local traffic mirroring, and API-backed
reputation checks, see `docs/sip-ifb-reputation.md`.

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
2.4.0-0.21.20260506gitfdc367f
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
- `/usr/libexec/geoipsets/update-all`: runs the full refresh sequence for systemd
- `/usr/libexec/geoipsets/reputation-worker`: reads Suricata EVE and promotes bad SIP sources
- `/usr/sbin/geoipsets-ifbctl`: optional SIP mirror helper for Suricata
- `/etc/geoipsets-reputation.env`: local reputation API and policy configuration
- `/usr/lib/systemd/system/geoipsets-reputation-worker.service`: optional local reputation worker
- `/usr/share/geoipsets/suricata/local-sip.rules`: local SIP rules for reputation signals
- `/usr/lib/tmpfiles.d/geoipsets.conf`: creates `/var/lib/geoipsets`
- `/var/lib/geoipsets`: generated provider output tree

The packaged default uses DB-IP, nftables output, and both IPv4 and IPv6. MaxMind
is supported by the application but requires users to add credentials in
`/etc/geoipsets.conf`.

`update-geoipsets.service` runs `/usr/libexec/geoipsets/update-all`. The wrapper
generates country data, refreshes country ipsets, fetches dynamic abuse feeds,
and refreshes `blocked_ipv4` and `blocked_ipv6`. If the DB-IP download fails,
the wrapper still refreshes abuse feeds and block ipsets, then exits nonzero so
the journal shows the country database failure.

The country ipset helper restores updated entries from
`/var/lib/geoipsets/dbip/ipset` using native set names such as `CA.ipv4` and
`CA.ipv6`. For older Shorewall configurations that expect names such as
`ipv4_CA` and `ipv6_CA`, run `/usr/libexec/geoipsets/refresh-ipset --legacy`.
Country ipsets are also auto-sized with 25% headroom during refresh.
To make the timer use legacy names, add a systemd drop-in:

```ini
[Service]
Environment=REFRESH_IPSET_ARGS=--legacy
```

If country sets need a larger minimum ipset size, add:

```ini
[Service]
Environment=COUNTRY_MAXELEM=2097152
```

Manual proxy, VPN, and abuse endpoints can be added to `/etc/geoipsets.blocklist`
or `/etc/geoipsets.blocklist.d/*.list` with one IP address or CIDR network per
line. Comments with `#` are allowed. Dynamic feeds are downloaded into
`/var/lib/geoipsets/blocklists/feeds/*.list`. Learned local lists can live under
`/var/lib/geoipsets/blocklists/*.list`. The refresh helper creates or updates
`blocked_ipv4` and `blocked_ipv6` with a temporary-set swap, so rules can
reference those sets while entries are updated. Blocklist ipsets use a default
minimum `maxelem` of `1048576` and auto-size upward with 25% headroom when the
loaded entry count exceeds that minimum.
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
    @blocklist_de https://lists.blocklist.de/lists/all.txt
    @techmdw https://blacklist.techmdw.com/
    @greensnow https://blocklist.greensnow.co/greensnow.txt
    @et https://rules.emergingthreats.net/fwrules/emerging-Block-IPs.txt
    @interserver https://rbldata.interserver.net/ip.txt
    @stopforumspam https://www.stopforumspam.com/downloads/toxic_ip_cidr.txt
    @spamhausdrop https://cascadiacrow.com/spamhausblocks.txt
    @spamhausdropv6 https://www.spamhaus.org/drop/dropv6.txt
    @blocklist_net_ua https://iplists.firehol.org/files/blocklist_net_ua.ipset
    @abuseipdb https://raw.githubusercontent.com/borestad/blocklist-abuseipdb/main/abuseipdb-s100-14d.ipv4
}
```

Only put block feeds in this file. Country allowlists such as `@ipv4_CA` and
`@ipv4_US` belong in geo policy sets, not in the blocklist feed config.

Because the feed config is installed as `%config(noreplace)`, RPM may install
updated defaults as `/etc/geoipsets.blocklist-feeds.conf.rpmnew`. Merge or
replace the existing file if you want the new default feeds enabled.

If very large feeds need a larger minimum ipset size, add a systemd drop-in:

```ini
[Service]
Environment=BLOCKLIST_MAXELEM=2097152
```

For a one-time manual refresh:

```bash
sudo /usr/libexec/geoipsets/refresh-blocklist --maxelem 2097152
```

`output-dir` is the parent directory used by the application. The Python code
appends `geoipsets/` internally, so the packaged `output-dir=/var/lib` writes
generated files under `/var/lib/geoipsets`.

`geoipsets-ifbctl` mirrors selected SIP ports to a local capture interface. The
default backend is a dummy interface named `ifb-sip0`, which works well for
local `tcpdump` and Suricata capture. Use `MIRROR_TYPE=ifb` only when an IFB
device is specifically required. Example Shorewall hook:

```bash
WAN_IF="ens18" MIRROR_TYPE=dummy SIP_PORTS="5060 5061 5084 5086 5087 5088" /usr/sbin/geoipsets-ifbctl start
```

The optional `geoipsets-reputation-worker.service` tails Suricata EVE JSON,
checks suspicious SIP sources with local API keys, and promotes confirmed bad
addresses into `blocked_ipv4` or `blocked_ipv6`. It also deletes active
conntrack state and appends confirmed blocks to
`/var/lib/geoipsets/blocklists/learned.list` so they survive refreshes.

Configure local API keys in `/etc/geoipsets-reputation.env`:

```bash
IPQS_API_KEY=replace-with-ipqualityscore-key
ABUSEIPDB_API_KEY=replace-with-abuseipdb-key
```

Then enable the worker:

```bash
sudo systemctl enable --now geoipsets-reputation-worker.service
```

The package also ships local Suricata rules under:

```text
/usr/share/geoipsets/suricata/local-sip.rules
```

Copy or include that file as `local-sip.rules` in the Suricata rules directory,
then add it to the local rule manager group list.

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
