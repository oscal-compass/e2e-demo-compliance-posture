#!/usr/bin/env bash

version_tag=$(semantic-release print-version)
echo "Preparing release ${version_tag}"
export VERSION_TAG="$version_tag"
echo "VERSION_TAG=${VERSION_TAG}" >> "$GITHUB_ENV"
git config --global user.email "automation@example.com"
git config --global user.name "Automation Bot" 
semantic-release publish
