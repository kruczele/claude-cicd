#!/bin/bash
set -e

# Check for the latest GitHub Actions runner version
echo "Checking for latest GitHub Actions runner version..."

LATEST_VERSION=$(curl -s https://api.github.com/repos/actions/runner/releases/latest | jq -r .tag_name | sed 's/^v//')
CURRENT_VERSION=$(cat VERSION 2>/dev/null || echo "unknown")

echo "Current version: $CURRENT_VERSION"
echo "Latest version:  $LATEST_VERSION"

if [ "$CURRENT_VERSION" != "$LATEST_VERSION" ]; then
    echo ""
    echo "⚠️  New version available!"
    echo "Run: ./scripts/update-version.sh $LATEST_VERSION"
    exit 1
else
    echo ""
    echo "✓ You are using the latest version"
    exit 0
fi
