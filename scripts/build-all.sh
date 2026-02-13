#!/bin/bash
set -e

# Build all runner images
echo "Building all GitHub Actions runner images..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Build all platforms
"$SCRIPT_DIR/build.sh" all "$@"

echo ""
echo "All runners built successfully!"
echo ""
echo "To run a runner:"
echo "  docker run -e GITHUB_TOKEN=<token> -e GITHUB_REPOSITORY=<owner/repo> ghcr.io/actions-runner:ubuntu-x64-latest"
