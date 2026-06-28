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
install -pm 0644 "${spec}" "${spec_dir}/geoipsets.spec"

rpmbuild -ba "${spec_dir}/geoipsets.spec" \
  --define "_topdir ${rpmbuild_dir}"
