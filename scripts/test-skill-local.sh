#!/bin/bash
# Test the skill runner locally without Docker

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration
SKILL="${1:-triage}"
TASK_INPUT="${2:-$PROJECT_ROOT/examples/task-input-example.yaml}"
WORKSPACE="${3:-$PROJECT_ROOT/workspace}"
OUTPUT="${4:-$PROJECT_ROOT/output}"

echo "🧪 Testing Skill Runner Locally"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Skill: $SKILL"
echo "Task Input: $TASK_INPUT"
echo "Workspace: $WORKSPACE"
echo "Output: $OUTPUT"
echo ""

# Create directories if they don't exist
mkdir -p "$WORKSPACE"
mkdir -p "$OUTPUT"

# Check if task input exists
if [ ! -f "$TASK_INPUT" ]; then
    echo "❌ Task input file not found: $TASK_INPUT"
    exit 1
fi

# Run the skill entrypoint
export SKILL="$SKILL"
export TASK_INPUT_PATH="$TASK_INPUT"
export OUTPUT_PATH="$OUTPUT"
export WORKSPACE_PATH="$WORKSPACE"
export ARTIFACTS_PATH="$PROJECT_ROOT/artifacts"
export CLAUDE_MODEL="${CLAUDE_MODEL:-claude-sonnet-4-5-20250929}"

echo "🚀 Running skill: $SKILL"
echo ""

python3 "$PROJECT_ROOT/scripts/skill-entrypoint.py" \
    --skill "$SKILL" \
    --task-input "$TASK_INPUT" \
    --output "$OUTPUT" \
    --workspace "$WORKSPACE"

EXIT_CODE=$?

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Skill execution successful"
    echo ""
    echo "Output files:"
    ls -lh "$OUTPUT"
else
    echo "❌ Skill execution failed with exit code: $EXIT_CODE"
fi

exit $EXIT_CODE
