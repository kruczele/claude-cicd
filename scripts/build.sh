#!/bin/bash
set -e

# Build script for GitHub Actions runner images
# Usage: ./build.sh <platform> [options]

PLATFORM=$1
RUNNER_VERSION=$(cat VERSION 2>/dev/null || echo "2.321.0")
REGISTRY=${REGISTRY:-"ghcr.io"}
IMAGE_NAME=${IMAGE_NAME:-"actions-runner"}

usage() {
    echo "Usage: $0 <platform> [options]"
    echo ""
    echo "Platforms:"
    echo "  ubuntu-x64      Build x64 Ubuntu runner"
    echo "  ubuntu-arm64    Build ARM64 Ubuntu runner"
    echo "  all             Build all platforms"
    echo ""
    echo "Options:"
    echo "  --version       Runner version (default: from VERSION file)"
    echo "  --push          Push to registry after building"
    echo "  --registry      Container registry (default: ghcr.io)"
    echo "  --tag           Additional tag (default: latest)"
    echo ""
    echo "Environment variables:"
    echo "  REGISTRY        Container registry"
    echo "  IMAGE_NAME      Base image name"
    echo "  GITHUB_REPOSITORY  GitHub repository (for image path)"
    exit 1
}

if [ -z "$PLATFORM" ]; then
    usage
fi

# Parse additional arguments
PUSH=false
CUSTOM_TAG="latest"

while [[ $# -gt 1 ]]; do
    case $2 in
        --version)
            RUNNER_VERSION="$3"
            shift 2
            ;;
        --push)
            PUSH=true
            shift
            ;;
        --registry)
            REGISTRY="$3"
            shift 2
            ;;
        --tag)
            CUSTOM_TAG="$3"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

build_platform() {
    local platform=$1
    local arch=$2

    echo "Building $platform runner (version: $RUNNER_VERSION)..."

    local image_tag="${REGISTRY}/${IMAGE_NAME}:${platform}-${RUNNER_VERSION}"
    local latest_tag="${REGISTRY}/${IMAGE_NAME}:${platform}-${CUSTOM_TAG}"

    # Build the image
    docker buildx build \
        --platform linux/${arch} \
        --build-arg RUNNER_VERSION=${RUNNER_VERSION} \
        -t ${image_tag} \
        -t ${latest_tag} \
        -f runners/${platform}/Dockerfile \
        runners/${platform}/ \
        ${PUSH:+--push} \
        --load

    echo "✓ Built ${image_tag}"
    echo "✓ Tagged as ${latest_tag}"

    if [ "$PUSH" = true ]; then
        echo "✓ Pushed to registry"
    fi
}

case $PLATFORM in
    ubuntu-x64)
        build_platform "ubuntu-x64" "amd64"
        ;;
    ubuntu-arm64)
        build_platform "ubuntu-arm64" "arm64"
        ;;
    all)
        build_platform "ubuntu-x64" "amd64"
        build_platform "ubuntu-arm64" "arm64"
        ;;
    *)
        echo "Error: Unknown platform '$PLATFORM'"
        usage
        ;;
esac

echo ""
echo "Build complete!"
