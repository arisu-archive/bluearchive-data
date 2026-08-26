#!/usr/bin/env bash

set -euo pipefail

version=$("$RUNNER_TEMP/bin/assets-dumper" version -s "$SERVER")
if [[ -z "$version" ]]; then
  echo "skip=true" >> "$GITHUB_OUTPUT"
  exit 0
fi
if [[ ! "$version" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "::error title=Invalid Resources Version::assets-dumper returned an invalid version"
  exit 1
fi

version_without_patch=$("$RUNNER_TEMP/bin/assets-dumper" version -s "$SERVER" --without-patch)
version_without_patch=${version_without_patch%-}
if [[ ! "$version_without_patch" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "::error title=Invalid Resources Version::assets-dumper returned an invalid version without patch"
  exit 1
fi

current=
if [[ -f "$SERVER.txt" ]]; then
  current=$(<"$SERVER.txt")
fi

skip=false
if [[ "$FORCE_UPDATE" != "true" && "$current" == "$version" ]]; then
  skip=true
fi

{
  echo "version=$version"
  echo "version_without_patch=$version_without_patch"
  echo "skip=$skip"
} >> "$GITHUB_OUTPUT"
echo "::notice title=Latest Resources Version::$version"
