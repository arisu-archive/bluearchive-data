#!/bin/bash

set -e

server=$1
forced_update=$2
version_file=$3

git config --global url."git@github.com:arisu-archive".insteadOf "https://github.com/arisu-archive"
go env -w GOPRIVATE="github.com/arisu-archive"
latest_version=$(go run github.com/arisu-archive/assets-dumper@latest version -s $server)
git config --global --remove-section url."git@github.com:arisu-archive"
echo "version=$latest_version" >> $GITHUB_OUTPUT
echo "::notice title=Latest Resources Version::$latest_version"
if [ -z "$latest_version" ]; then
    echo "Latest version not found. Skipping..."
    echo "skip=true" >> $GITHUB_OUTPUT
    exit 0
fi

if [ "$forced_update" = "true" ]; then
    echo "Forced update. Skipping..."
    echo "skip=false" >> $GITHUB_OUTPUT
    echo -n "$latest_version" > $version_file
    exit 0
fi

current_version=$(cat $version_file)
echo "Current version: $current_version"
if [ "$current_version" = "$latest_version" ]; then
    echo "No update needed. Skipping..."
    echo "skip=true" >> $GITHUB_OUTPUT
    echo -n "$latest_version" > $version_file
    exit 0
fi
echo "skip=false" >> $GITHUB_OUTPUT
echo -n "$latest_version" > $version_file
