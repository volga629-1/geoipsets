#!/usr/bin/bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
spec="${repo_root}/rpm/geoipsets.spec"
rpmbuild_dir="${RPM_TOPDIR:-${HOME}/rpmbuild}"
source_dir="${rpmbuild_dir}/SOURCES"
spec_dir="${rpmbuild_dir}/SPECS"

commit="$(awk '/^%global commit/ {print $3}' "${spec}")"
shortcommit="${commit:0:7}"
archive="${source_dir}/geoipsets-${shortcommit}.tar.gz"
prefix="geoipsets-${commit}"

if [[ ! -d "${rpmbuild_dir}"/BUILD ]]; then
    mkdir -p "${rpmbuild_dir}"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
fi

tar -C "${repo_root}" \
  --exclude=.git \
  --exclude=rpm/build \
  --transform "s,^\.,${prefix}," \
  -czf "${archive}" .

install -pm 0644 "${repo_root}/rpm/geoipsets.conf" "${source_dir}/geoipsets.conf"
install -pm 0644 "${repo_root}/rpm/update-geoipsets.service" "${source_dir}/update-geoipsets.service"
install -pm 0644 "${repo_root}/rpm/update-geoipsets.timer" "${source_dir}/update-geoipsets.timer"
install -pm 0644 "${repo_root}/rpm/geoipsets.tmpfiles" "${source_dir}/geoipsets.tmpfiles"
install -pm 0755 "${repo_root}/rpm/geoipsets-refresh-ipset" "${source_dir}/geoipsets-refresh-ipset"
install -pm 0644 "${repo_root}/rpm/geoipsets.blocklist" "${source_dir}/geoipsets.blocklist"
install -pm 0755 "${repo_root}/rpm/geoipsets-refresh-blocklist" "${source_dir}/geoipsets-refresh-blocklist"
install -pm 0644 "${repo_root}/rpm/geoipsets.blocklist-feeds.conf" "${source_dir}/geoipsets.blocklist-feeds.conf"
install -pm 0755 "${repo_root}/rpm/geoipsets-fetch-blocklists" "${source_dir}/geoipsets-fetch-blocklists"
install -pm 0755 "${repo_root}/rpm/geoipsets-ifbctl" "${source_dir}/geoipsets-ifbctl"
install -pm 0755 "${repo_root}/rpm/geoipsets-update-all" "${source_dir}/geoipsets-update-all"
install -pm 0640 "${repo_root}/rpm/geoipsets-reputation.env" "${source_dir}/geoipsets-reputation.env"
install -pm 0755 "${repo_root}/rpm/geoipsets-reputation-worker" "${source_dir}/geoipsets-reputation-worker"
install -pm 0644 "${repo_root}/rpm/geoipsets-reputation-worker.service" "${source_dir}/geoipsets-reputation-worker.service"
install -pm 0644 "${repo_root}/rpm/geoipsets-local-sip.rules" "${source_dir}/geoipsets-local-sip.rules"
install -pm 0755 "${repo_root}/rpm/geoipsets-provision-sip-suricata" "${source_dir}/geoipsets-provision-sip-suricata"
install -pm 0644 "${spec}" "${spec_dir}/geoipsets.spec"

rpmbuild -ba "${spec_dir}/geoipsets.spec" \
  --define "_topdir ${rpmbuild_dir}"
