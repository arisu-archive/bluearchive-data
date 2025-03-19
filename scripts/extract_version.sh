#!/bin/bash

package_name=$1
forced_update=$2
version_file=$3

latest_version=$(curl -s https://ba.pokeguy.dev/$package_name/version.txt)
echo "version=$latest_version" >> $GITHUB_OUTPUT
echo "::notice title=Latest APK Version::$latest_version"
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
