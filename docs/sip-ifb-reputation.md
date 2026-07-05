# SIP Mirror Interface and Reputation Blocking

This design keeps SIP traffic on the normal Shorewall path, mirrors a copy to a
local inspection interface, and lets a reputation worker add bad sources to
the `blocked_ipv4` and `blocked_ipv6` ipsets.

The important rule is that packet forwarding must not wait for an external API.
Suricata and the reputation worker observe traffic out of band. Shorewall/ipset
remain the enforcement path.

## Flow

```text
WAN SIP traffic
    |
    +--> Shorewall normal rules
    |       |
    |       +--> drop if source is already in blocked_ipv4/blocked_ipv6
    |       +--> otherwise handle SIP normally
    |
    +--> tc mirror copy to ifb-sip0
            |
            +--> Suricata watches ifb-sip0
                    |
                    +--> EVE JSON alert or SIP parser event
                            |
                            +--> reputation worker checks local cache/API
                                    |
                                    +--> if bad: ipset add + conntrack delete + persist
                                    +--> if clean: cache checked result
```

## Packages

On Fedora:

```bash
sudo dnf install iproute-tc ipset conntrack-tools suricata jq curl
```

When using the RPM package, `geoipsets-ifbctl` provides the mirror setup helper:

```bash
geoipsets-ifbctl start
geoipsets-ifbctl status
geoipsets-ifbctl stop
geoipsets-ifbctl restart
```

By default it mirrors SIP ports `5060 5061 5084` to a dummy-backed
`ifb-sip0` interface and auto-detects the IPv4 and IPv6 default-route
interfaces. A dummy mirror is preferred for passive local capture because
`tcpdump` and Suricata can read the mirrored packets directly. Override
defaults with environment variables:

```bash
WAN_IF="ens3" MIRROR_TYPE=dummy MIRROR_IF=ifb-sip0 SIP_PORTS="5060 5061 5084" geoipsets-ifbctl start
```

`start` resets the managed `clsact` qdisc before installing mirror filters, so
Shorewall restarts and port-list changes do not leave stale filters behind.
It also replaces an existing mirror interface if the interface name exists with
the wrong kernel type.

Optional for a local cache:

```bash
sudo dnf install sqlite
```

## Create the Mirror Interface

Replace `eth0` with the public/WAN interface that receives SIP traffic.

```bash
wan_if=eth0
mirror_if=ifb-sip0

sudo ip link add "${mirror_if}" type dummy 2>/dev/null || true
sudo ip link set "${mirror_if}" txqueuelen 10000
sudo ip link set "${mirror_if}" up promisc on
```

If an IFB device is specifically required, use `MIRROR_TYPE=ifb` with
`geoipsets-ifbctl` or create it manually with `ip link add "${mirror_if}" type ifb`.

## NetworkManager and nmcli

On systems managed by NetworkManager, check whether the installed
NetworkManager build exposes an IFB connection type:

```bash
nmcli connection add type help | grep -w ifb
```

If `ifb` is listed, NetworkManager can create the mirror interface:

```bash
sudo modprobe ifb
sudo nmcli connection add type ifb ifname ifb-sip0 con-name ifb-sip0 \
  ipv4.method disabled \
  ipv6.method disabled
sudo nmcli connection modify ifb-sip0 connection.autoconnect yes
sudo nmcli connection up ifb-sip0
```

If `ifb` is not listed, create the interface with `ip link` or the systemd
helper below. NetworkManager can still coexist with that interface, but it
cannot create an unsupported kernel link type through `nmcli`.

`nmcli` only handles the interface lifecycle. The `tc` mirror filters still need
to be applied separately after boot and after relevant network changes.

Use `clsact` so only ingress filters are added to the WAN interface. This
mirrors packets to `ifb-sip0`; it does not redirect or delay the original packet.

```bash
sudo tc qdisc add dev "${wan_if}" clsact 2>/dev/null || true
```

Mirror common SIP ports. Add or remove ports to match the local SIP edge.

```bash
for port in 5060 5061 5084; do
  sudo tc filter add dev "${wan_if}" ingress protocol ip pref "$((100 + port))" flower \
    ip_proto udp dst_port "${port}" \
    action mirred egress mirror dev "${mirror_if}"

  sudo tc filter add dev "${wan_if}" ingress protocol ip pref "$((200 + port))" flower \
    ip_proto tcp dst_port "${port}" \
    action mirred egress mirror dev "${mirror_if}"

  sudo tc filter add dev "${wan_if}" ingress protocol ipv6 pref "$((300 + port))" flower \
    ip_proto udp dst_port "${port}" \
    action mirred egress mirror dev "${mirror_if}"

  sudo tc filter add dev "${wan_if}" ingress protocol ipv6 pref "$((400 + port))" flower \
    ip_proto tcp dst_port "${port}" \
    action mirred egress mirror dev "${mirror_if}"
done
```

Check the filters:

```bash
sudo tc filter show dev "${wan_if}" ingress
```

Test the mirror:

```bash
sudo tcpdump -ni "${mirror_if}" 'port 5060 or port 5061 or port 5084'
```

## Remove the Mirror

```bash
wan_if=eth0
mirror_if=ifb-sip0

sudo tc qdisc del dev "${wan_if}" clsact 2>/dev/null || true
sudo ip link del "${mirror_if}" 2>/dev/null || true
```

## Make the Mirror Persistent

`tc` rules are runtime state. Reapply them after boot or after network changes.
Even when `nmcli` creates `ifb-sip0`, a separate hook is still needed for the
`tc` filters. One simple approach is a oneshot systemd service.

For Shorewall, the simplest hook is `/etc/shorewall/started`:

```bash
#!/usr/bin/bash
WAN_IF="ens3" MIRROR_TYPE=dummy SIP_PORTS="5060 5061 5084 5086 5087 5088" /usr/sbin/geoipsets-ifbctl start
return 0
```

If `WAN_IF` is omitted, the helper detects IPv4 and IPv6 default-route
interfaces and applies mirror filters to each unique interface.

For non-RPM installs, the same behavior can be implemented with a local helper.
Create `/usr/local/sbin/geoipsets-ifb-mirror`:

```bash
#!/usr/bin/bash
set -euo pipefail

wan_if="${WAN_IF:-eth0}"
mirror_if="${MIRROR_IF:-ifb-sip0}"
ports="${SIP_PORTS:-5060 5061 5084}"

ip link add "${mirror_if}" type dummy 2>/dev/null || true
ip link set "${mirror_if}" txqueuelen 10000
ip link set "${mirror_if}" up promisc on

tc qdisc add dev "${wan_if}" clsact 2>/dev/null || true

for port in ${ports}; do
  tc filter add dev "${wan_if}" ingress protocol ip pref "$((100 + port))" flower \
    ip_proto udp dst_port "${port}" \
    action mirred egress mirror dev "${mirror_if}" 2>/dev/null || true

  tc filter add dev "${wan_if}" ingress protocol ip pref "$((200 + port))" flower \
    ip_proto tcp dst_port "${port}" \
    action mirred egress mirror dev "${mirror_if}" 2>/dev/null || true

  tc filter add dev "${wan_if}" ingress protocol ipv6 pref "$((300 + port))" flower \
    ip_proto udp dst_port "${port}" \
    action mirred egress mirror dev "${mirror_if}" 2>/dev/null || true

  tc filter add dev "${wan_if}" ingress protocol ipv6 pref "$((400 + port))" flower \
    ip_proto tcp dst_port "${port}" \
    action mirred egress mirror dev "${mirror_if}" 2>/dev/null || true
done
```

Create `/etc/systemd/system/geoipsets-ifb-mirror.service`:

```ini
[Unit]
Description=Mirror SIP traffic to local inspection interface
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
Environment=WAN_IF=eth0
Environment=MIRROR_IF=ifb-sip0
Environment=MIRROR_TYPE=dummy
Environment="SIP_PORTS=5060 5061 5084"
ExecStart=/usr/local/sbin/geoipsets-ifb-mirror
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

Enable it:

```bash
sudo chmod 0755 /usr/local/sbin/geoipsets-ifb-mirror
sudo systemctl daemon-reload
sudo systemctl enable --now geoipsets-ifb-mirror.service
```

If NetworkManager events are preferred, run the same helper from a dispatcher
script after the WAN connection comes up. Create
`/etc/NetworkManager/dispatcher.d/90-geoipsets-ifb-mirror`:

```bash
#!/usr/bin/bash
set -euo pipefail

wan_if="eth0"
mirror_if="ifb-sip0"
ports="5060 5061 5084"

event_if="$1"
event_state="$2"

[[ "${event_if}" == "${wan_if}" ]] || exit 0
[[ "${event_state}" == "up" || "${event_state}" == "dhcp4-change" || "${event_state}" == "dhcp6-change" ]] || exit 0

WAN_IF="${wan_if}" MIRROR_IF="${mirror_if}" SIP_PORTS="${ports}" /usr/local/sbin/geoipsets-ifb-mirror
```

Enable the dispatcher script:

```bash
sudo chmod 0755 /etc/NetworkManager/dispatcher.d/90-geoipsets-ifb-mirror
sudo systemctl reload NetworkManager
```

## Suricata Input

Configure Suricata to listen on the mirror interface:

```yaml
af-packet:
  - interface: ifb-sip0
    cluster-id: 99
    cluster-type: cluster_flow
    defrag: yes
```

Keep Suricata in IDS/passive mode first. The firewall should not depend on
Suricata for packet verdicts.

The RPM ships local SIP reputation signal rules here:

```text
/usr/share/geoipsets/suricata/local-sip.rules
```

Copy or include that file as `local-sip.rules` in the Suricata rules directory,
then add it to the local Suricata rule group list:

```text
group:emerging-dshield.rules
group:emerging-scan.rules
group:emerging-exploit.rules
group:emerging-voip.rules
group:emerging-dos.rules
group:emerging-malware.rules
group:emerging-worm.rules
group:tor.rules
group:local-sip.rules
classtype:trojan-activity
```

Treat `emerging-deleted.rules` as log-only while testing. It can include rules
removed upstream for age or quality reasons.

The local rules intentionally include a generic inbound INVITE reputation-check
alert. That alert is a trigger for API lookup only; it does not mean the source
is blocked. The worker blocks only after IPQS or AbuseIPDB confirms proxy, VPN,
Tor, recent abuse, or a high score.

If `tc -s filter show dev WAN ingress` shows mirrored packets but Suricata or
`tcpdump` sees nothing, switch the helper to the dummy backend:

```bash
WAN_IF=ens3 MIRROR_TYPE=dummy SIP_PORTS="5060 5061 5084 5086 5087 5088" geoipsets-ifbctl restart
tcpdump -ni ifb-sip0 -e -vv -s 0
```

## Example SIP Detection Rules

These rules are examples. Tune them against real traffic before enabling
automatic blocking.

```text
alert tcp any any -> $HOME_NET 5060:5089 (
  msg:"SIP INVITE with CGNAT/private Contact";
  flow:to_server,established;
  content:"INVITE sip:"; nocase;
  content:"Contact|3a|"; nocase;
  pcre:"/Contact\x3a.*@(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|100\.64\.)/i";
  classtype:attempted-recon;
  sid:9000001;
  rev:1;
)
```

```text
alert tcp any any -> $HOME_NET 5060:5089 (
  msg:"SIP SDP advertises private or CGNAT media address";
  flow:to_server,established;
  content:"INVITE sip:"; nocase;
  pcre:"/\nc=IN IP4 (10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|100\.64\.)/i";
  classtype:attempted-recon;
  sid:9000002;
  rev:1;
)
```

For UDP SIP, remove `flow:to_server,established` or create separate UDP rules.

## Reputation Worker

The RPM includes a stage-1 local worker:

```text
/usr/libexec/geoipsets/reputation-worker
/usr/lib/systemd/system/geoipsets-reputation-worker.service
/etc/geoipsets-reputation.env
```

The worker reads Suricata EVE JSON alerts and selected SIP parser events, groups
events by source IP, checks a local SQLite cache first, and only then calls
local API providers.

Do not call external APIs from packet path rules.

The API tokens live in a root-readable environment file, not inside Shorewall
rules or Suricata rules:

```text
/etc/geoipsets-reputation.env
```

Example:

```bash
IPQS_API_KEY=replace-with-real-token
ABUSEIPDB_API_KEY=replace-with-real-token
```

Enable the worker:

```bash
systemctl enable --now geoipsets-reputation-worker.service
journalctl -u geoipsets-reputation-worker.service -f
```

The packaged service joins the `suricata` supplementary group so it can read
`/var/log/suricata/eve.json` while still running with a reduced capability set.
If the service is installed manually, keep this setting:

```ini
[Service]
SupplementaryGroups=suricata
```

Local state:

```text
/var/lib/geoipsets/reputation/reputation.sqlite
/var/lib/geoipsets/blocklists/learned.list
/var/lib/geoipsets/blocklists/allow.list
```

The allow list accepts one IP or CIDR per line and prevents promotion of known
trusted SIP peers.

The worker supports:

```text
IPQualityScore: proxy, VPN, Tor, recent abuse, bot, and fraud score signals
AbuseIPDB: abuse confidence score and Tor signal
```

Recommended worker logic:

```text
read Suricata EVE alert
  |
  +-- ignore if event is not a SIP abuse SID
  +-- ignore private/reserved source addresses
  +-- ignore allowlisted source addresses
  +-- if source IP is already blocked: stop
  +-- if source IP was checked clean recently: log and stop
  +-- if source IP has repeated suspicious SIP parser events: check reputation
  +-- if source IP creates a Suricata alert: check reputation immediately
          |
          +-- IPQS and/or AbuseIPDB
          +-- cache result with expiry
          |
          +-- if VPN/proxy/Tor/recent abuse/high score:
                 ipset add blocked_ipv4 SRCIP -exist
                 conntrack -D -s SRCIP
                 append SRCIP to learned blocklist
```

Suggested cache fields:

```text
ip
first_seen
last_seen
last_checked
hit_count
suricata_sid
provider
score
vpn
proxy
tor
recent_abuse
decision
reason
expires_at
```

## API Check Policy

The reputation worker should group checks so the same IP is not queried
repeatedly. A simple policy is:

```text
if IP was checked clean in the last 24 hours:
  do not query API again

if IP is already blocked and not expired:
  do not query API again

if one low-confidence SIP event is seen:
  record only

if repeated SIP abuse events are seen within 10 minutes:
  query reputation

if high-confidence SIP rule is seen:
  query reputation immediately

if generic inbound SIP INVITE is seen:
  query reputation immediately
```

Example block policy:

```text
block if:
  vpn == true
  or proxy == true
  or tor == true
  or fraud_score >= 85
  or abuse_confidence >= 90
  or recent_abuse == true

block if:
  hosting/datacenter == true
  and repeated suspicious SIP events were seen
```

Avoid blocking on hosting/datacenter alone. Many valid SIP providers and
monitoring systems run from datacenter networks.

## Enforce a Positive Decision

For IPv4:

```bash
ipset add blocked_ipv4 45.146.55.104 -exist
conntrack -D -s 45.146.55.104 2>/dev/null || true
printf '%s\n' 45.146.55.104 >> /var/lib/geoipsets/blocklists/learned.list
```

For IPv6:

```bash
ipset add blocked_ipv6 2001:db8::bad -exist
conntrack -D -s 2001:db8::bad 2>/dev/null || true
printf '%s\n' 2001:db8::bad >> /var/lib/geoipsets/blocklists/learned.list
```

The packaged `refresh-blocklist` helper should later load learned blocklist
files into `blocked_ipv4` and `blocked_ipv6` so blocks survive reboot and ipset
refreshes.

The worker performs the live `ipset add` immediately, so a bad source is blocked
before the next refresh.

## Shorewall Placement

Place ipset drops before normal SIP allow rules. The exact syntax depends on the
local Shorewall configuration, but the logical order should be:

```text
drop source in blocked_ipv4/blocked_ipv6
allow trusted SIP peers
allow public SIP policy
log/drop everything else
```

Keep the mirror independent from Shorewall policy. The mirror is only for
observation; Shorewall/ipset are still the enforcement layer.
