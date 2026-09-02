#!/usr/bin/env bash
set -euo pipefail

version=${1:?"Version fehlt"}
architecture=${2:?"Debian-Architektur fehlt"}
executable=${3:?"Pfad zur Nuitka-Datei fehlt"}
output_dir=${4:?"Ausgabeordner fehlt"}

package_root=$(mktemp -d)
package_name="codeclister_${version}_${architecture}"

cleanup() {
  rm -rf "$package_root"
}
trap cleanup EXIT

install -Dm755 "$executable" "$package_root/opt/CodecLister/CodecLister"
install -Dm644 src/codeclister/assets/icon.png \
  "$package_root/usr/share/icons/hicolor/256x256/apps/codeclister.png"
install -Dm644 packaging/linux/codeclister.desktop \
  "$package_root/usr/share/applications/codeclister.desktop"

mkdir -p "$package_root/DEBIAN"
cat > "$package_root/DEBIAN/control" <<EOF
Package: codeclister
Version: $version
Section: video
Priority: optional
Architecture: $architecture
Maintainer: CodecLister contributors
Description: List media codecs, resolutions and HDR metadata
 CodecLister scans media folders and lists technical file details.
EOF

mkdir -p "$output_dir"
dpkg-deb --root-owner-group --build "$package_root" "$output_dir/$package_name.deb"