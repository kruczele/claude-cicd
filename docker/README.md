# Claude Code Skill Runner - Docker Setup

Single unified Docker image that runs all Claude Code skills (triage, execute, pre-verify, verify, devils-advocate).

## Quick Start

### 1. Build the Image

```bash
cd /home/krukon/gh/cicd
./scripts/build-image.sh
```

### 2. Run a Skill

```bash
docker run -it --rm \
  -v $(pwd)/examples/task-input-example.yaml:/input/task-input.yaml \
  -v $(pwd)/workspace:/workspace \
  -v $(pwd)/output:/output \
  -e SKILL=triage \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  claude-skill-runner:latest
```

### 3. Check Output

```bash
ls -la output/
cat output/state.md
cat output/feedback.md
cat output/execution-summary.json
```

## Environment Variables

### Required
- `SKILL` - Which skill to run (triage, execute, pre-verify, verify, devils-advocate)
- `ANTHROPIC_API_KEY` - Your Claude API key

### Optional
- `CLAUDE_MODEL` - Model to use (default: claude-sonnet-4-5-20250929)
- `TASK_INPUT_PATH` - Path to task input YAML (default: /input/task-input.yaml)
- `OUTPUT_PATH` - Where to write outputs (default: /output)
- `WORKSPACE_PATH` - Code workspace directory (default: /workspace)
- `ARTIFACTS_PATH` - Artifacts directory (default: /artifacts)
- `GITHUB_TOKEN` - For PR/issue operations

### Git Configuration
- `GIT_AUTHOR_NAME` - Git commit author name
- `GIT_AUTHOR_EMAIL` - Git commit author email

## Volume Mounts

### Required Mounts
- `/workspace` - Your code repository (read/write)
- `/input` - Directory containing task-input.yaml (read-only)
- `/output` - Where skill outputs are written (write)

### Optional Mounts
- `/artifacts` - Persistent artifacts across runs
- `/root/.ssh` - SSH keys for git operations (read-only)
- `/var/run/docker.sock` - For nested containers (if needed)

## What's Included

### Core Tools
- **Ubuntu 24.04 LTS** - Base OS
- **Python 3** - With pip, venv, common packages
- **Node.js 20** - With npm
- **Go 1.21** - For Go projects
- **Rust** - Via rustup

### Browser Automation
- **Google Chrome Stable** - Headless browser
- **Playwright** - Browser automation (Chromium, Firefox, WebKit)

### CLI Tools
- **jq** - JSON processing
- **yq** - YAML processing
- **ripgrep** - Fast text search
- **fd-find** - Fast file finding
- **bat** - Better cat with syntax highlighting
- **curl, wget** - HTTP clients
- **git** - Version control
- **gh** - GitHub CLI

### Development Tools
- **docker-ce-cli** - Docker client (for nested scenarios)
- **pytest, black, flake8, mypy** - Python tooling
- Build essentials (gcc, make, etc.)

## Usage Examples

### Example 1: Triage a Task

```bash
# Create task input
cat > task-input.yaml <<EOF
task_id: "task-001"
skill: "triage"
task:
  title: "Add authentication"
  description: "Implement JWT-based auth"
git:
  target_branch: "feature/auth"
  main_branch: "main"
EOF

# Run triage
docker run -it --rm \
  -v $(pwd)/task-input.yaml:/input/task-input.yaml \
  -v $(pwd)/myproject:/workspace \
  -v $(pwd)/output:/output \
  -e SKILL=triage \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  claude-skill-runner:latest

# Check results
cat output/triage-plan.yaml
```

### Example 2: Execute Implementation

```bash
docker run -it --rm \
  -v $(pwd)/task-input.yaml:/input/task-input.yaml \
  -v $(pwd)/myproject:/workspace \
  -v $(pwd)/output:/output \
  -v ~/.ssh:/root/.ssh:ro \
  -e SKILL=execute \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  -e GITHUB_TOKEN=$GITHUB_TOKEN \
  claude-skill-runner:latest

# Check state
cat output/state.md
cat output/feedback.md
```

### Example 3: Verify Changes

```bash
docker run -it --rm \
  -v $(pwd)/task-input.yaml:/input/task-input.yaml \
  -v $(pwd)/validation-strategy.md:/input/validation-strategy.md \
  -v $(pwd)/myproject:/workspace \
  -v $(pwd)/output:/output \
  -e SKILL=verify \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  claude-skill-runner:latest

# Check results
cat output/verification-results.md
```

### Example 4: Devils-Advocate Analysis

```bash
docker run -it --rm \
  -v $(pwd)/task-input.yaml:/input/task-input.yaml \
  -v $(pwd)/verification-history:/artifacts/verification-history \
  -v $(pwd)/myproject:/workspace \
  -v $(pwd)/output:/output \
  -e SKILL=devils-advocate \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  claude-skill-runner:latest

# Check analysis
cat output/assumption-analysis.md
```

## Docker Compose

For easier orchestration, use docker-compose:

```bash
# Set environment variables
export ANTHROPIC_API_KEY=your-key
export WORKSPACE_PATH=/path/to/your/code
export SKILL=triage

# Run
cd docker
docker-compose up skill-runner

# Or with Prefect orchestration
docker-compose up  # Starts skill-runner + Prefect server + agent
```

## Building for Different Platforms

### ARM64 (e.g., Apple Silicon)
```bash
IMAGE_TAG=arm64 PLATFORM=linux/arm64 ./scripts/build-image.sh
```

### Multi-arch
```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag claude-skill-runner:latest \
  --file docker/Dockerfile \
  --push \
  .
```

## Troubleshooting

### Issue: "Claude Code CLI not found"
The Dockerfile has a placeholder for Claude CLI installation. Update with actual installation method:
```dockerfile
RUN curl -fsSL https://actual-install-url.sh | bash
```

### Issue: "Permission denied" on /workspace
Ensure the mounted directory has correct permissions:
```bash
chmod -R 755 /path/to/workspace
```

### Issue: "Git authentication failed"
Mount SSH keys with correct permissions:
```bash
docker run -v ~/.ssh:/root/.ssh:ro ...
```

Or use HTTPS with token:
```bash
-e GIT_CREDENTIALS="https://user:token@github.com"
```

### Issue: "Browser tests failing"
Ensure Chrome/Playwright are properly configured:
```bash
docker run --cap-add=SYS_ADMIN ...  # Chrome needs this
```

Or run in headless mode:
```bash
-e PLAYWRIGHT_HEADLESS=true
```

## Performance Tuning

### Memory
Default: 8GB limit. Adjust in docker-compose.yml or:
```bash
docker run --memory=16g ...
```

### CPU
Default: 4 CPU limit. Adjust:
```bash
docker run --cpus=8 ...
```

### Cache
Mount a cache directory to speed up repeated builds:
```bash
-v ~/.claude-cache:/root/.claude-cache
```

## Security

### API Keys
Never bake API keys into the image. Always pass via environment variables.

### Secrets
For sensitive data, use Docker secrets:
```bash
echo "$SECRET" | docker secret create api_key -
docker run --secret api_key ...
```

### Network Isolation
Run in custom network for isolation:
```bash
docker network create claude-net
docker run --network claude-net ...
```

## Integration with CI/CD

### GitHub Actions
```yaml
- name: Run Claude Skill
  run: |
    docker run \
      -v ${{ github.workspace }}:/workspace \
      -v ./task-input.yaml:/input/task-input.yaml \
      -v ./output:/output \
      -e SKILL=execute \
      -e ANTHROPIC_API_KEY=${{ secrets.ANTHROPIC_API_KEY }} \
      claude-skill-runner:latest
```

### GitLab CI
```yaml
claude-skill:
  image: claude-skill-runner:latest
  variables:
    SKILL: execute
    ANTHROPIC_API_KEY: $ANTHROPIC_API_KEY
  script:
    - /app/scripts/skill-entrypoint.py
```

## Health Checks

The container includes a health check:
```bash
docker ps  # Check HEALTH column
```

Health check looks for `/tmp/skill-runner-healthy` file created by successful execution.

## Logs

View logs:
```bash
docker logs <container-id>
```

Follow logs:
```bash
docker logs -f <container-id>
```

## Next Steps

1. **Update Claude CLI installation** in Dockerfile with actual method
2. **Test each skill** with real tasks
3. **Optimize image size** (currently ~4GB, can be reduced)
4. **Add caching layers** for faster rebuilds
5. **Set up image registry** for distribution
6. **Configure Prefect** for orchestration

## Support

For issues, see:
- Main README: `/CLAUDE_CICD.md`
- Skill definitions: `/skills/*.yaml`
- Prefect flows: `/orchestration/prefect_flows.py`
