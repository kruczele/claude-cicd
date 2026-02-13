#!/bin/bash
# Build the unified Claude Code skill runner image

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

IMAGE_NAME="${IMAGE_NAME:-claude-skill-runner}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
PLATFORM="${PLATFORM:-linux/amd64}"

echo "🐳 Building Claude Code Skill Runner"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Image: $IMAGE_NAME:$IMAGE_TAG"
echo "Platform: $PLATFORM"
echo "Context: $PROJECT_ROOT"
echo ""

cd "$PROJECT_ROOT"

# Build the image
docker build \
    --platform "$PLATFORM" \
    --tag "$IMAGE_NAME:$IMAGE_TAG" \
    --file docker/Dockerfile \
    --progress=plain \
    .

echo ""
echo "✅ Build complete!"
echo ""
echo "Run with:"
echo "  docker run -it --rm \\"
echo "    -v \$(pwd):/workspace \\"
echo "    -v /path/to/task-input.yaml:/input/task-input.yaml \\"
echo "    -v /path/to/output:/output \\"
echo "    -e SKILL=execute \\"
echo "    -e ANTHROPIC_API_KEY=\$ANTHROPIC_API_KEY \\"
echo "    $IMAGE_NAME:$IMAGE_TAG"
echo ""
echo "Test with:"
echo "  docker run -it --rm $IMAGE_NAME:$IMAGE_TAG --help"
