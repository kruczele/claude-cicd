#!/bin/bash
set -e

# Update GitHub Actions runner version across all Dockerfiles
# Usage: ./update-version.sh <new-version>
# Example: ./update-version.sh 2.322.0

NEW_VERSION=$1

if [ -z "$NEW_VERSION" ]; then
    echo "Usage: $0 <new-version>"
    echo "Example: $0 2.322.0"
    exit 1
fi

# Validate version format (e.g., 2.321.0)
if ! [[ "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: Invalid version format. Expected format: X.Y.Z (e.g., 2.321.0)"
    exit 1
fi

echo "Updating runner version to $NEW_VERSION..."

# Update VERSION file
echo "$NEW_VERSION" > VERSION
echo "✓ Updated VERSION file"

# Update ubuntu-x64 Dockerfile
sed -i "s/ARG RUNNER_VERSION=.*/ARG RUNNER_VERSION=$NEW_VERSION/" runners/ubuntu-x64/Dockerfile
echo "✓ Updated runners/ubuntu-x64/Dockerfile"

# Update ubuntu-arm64 Dockerfile
sed -i "s/ARG RUNNER_VERSION=.*/ARG RUNNER_VERSION=$NEW_VERSION/" runners/ubuntu-arm64/Dockerfile
echo "✓ Updated runners/ubuntu-arm64/Dockerfile"

echo ""
echo "Version updated to $NEW_VERSION successfully!"
echo ""
echo "Next steps:"
echo "  1. Review the changes: git diff"
echo "  2. Build new images: ./scripts/build-all.sh"
echo "  3. Test the runners"
echo "  4. Commit changes: git commit -am 'Update runner version to $NEW_VERSION'"
