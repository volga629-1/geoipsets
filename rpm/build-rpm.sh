#!/usr/bin/bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
spec="${repo_root}/rpm/geoipsets.spec"
build_root="${repo_root}/rpm/build"
source_dir="${build_root}/SOURCES"
rpmbuild_dir="${build_root}/rpmbuild"

commit="$(git -C "${repo_root}" rev-parse HEAD)"
shortcommit="${commit:0:7}"
archive="${source_dir}/geoipsets-${shortcommit}.tar.gz"
prefix="geoipsets-${commit}"

if [[ ! -d "${rpmbuild_dir}"/BUILD ]]; then
    mkdir -p "${source_dir}" "${rpmbuild_dir}"/{BUILD,BUILDROOT,RPMS,SPECS,SRPMS}
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

rpmbuild -ba "${spec}" \
  --define "_topdir ${rpmbuild_dir}" \
  --define "_sourcedir ${source_dir}" \
  --define "_srcrpmdir ${rpmbuild_dir}/SRPMS" \
  --define "_rpmdir ${rpmbuild_dir}/RPMS"
