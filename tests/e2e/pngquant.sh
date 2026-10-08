#!/usr/bin/env bash

# Install pngquant in the Playwright image of screenshots.sh, the Ubuntu 24.04 it
# is built on: the exact packages of the release, checked against their SHA-256,
# so that the compressed screenshots come out the same, byte for byte, until this
# pin changes. Launchpad keeps every published package at its address.

set -euo pipefail

PACKAGES=(
	"pngquant_2.18.0-1build2_amd64.deb 924fe4b18c86e9314b5667ea4945916f320e8c785f14a5e99edd2d370441164c"
	"libimagequant0_2.18.0-1build1_amd64.deb 94bfa8908323a469292bd68ccae984414e8f5f1dc28cacbe952b7cbce36c6865"
)

if command -v pngquant >/dev/null 2>&1; then
	exit 0
fi
folder="$(mktemp -d)"
for package in "${PACKAGES[@]}"; do
	read -r file sha256 <<<"${package}"
	curl --fail --silent --show-error --location --retry 3 --output "${folder}/${file}" \
		"https://launchpad.net/ubuntu/+archive/primary/+files/${file}"
	echo "${sha256}  ${folder}/${file}" | sha256sum --check --strict --quiet
done
dpkg --install "${folder}"/*.deb >/dev/null
rm -rf "${folder}"
pngquant --version
