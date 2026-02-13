# Claude Code CI/CD Skill Runner
# Generic container for all skills (triage, execute, pre-verify, verify, devils-advocate)

FROM ubuntu:24.04

LABEL maintainer="Krukon <imprezobus@gmail.com>"
LABEL description="Unified Claude Code skill runner with browser automation and CI/CD tools"
LABEL version="1.0.0"

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# ============================================================================
# System Dependencies
# ============================================================================

RUN apt-get update && apt-get install -y \
    # Core utilities
    curl \
    wget \
    git \
    unzip \
    gnupg \
    ca-certificates \
    software-properties-common \
    apt-transport-https \
    lsb-release \
    # Build essentials
    build-essential \
    python3 \
    python3-full \
    python3-pip \
    python3-venv \
    # CLI tools for CI/CD
    jq \
    yq \
    # Text processing
    ripgrep \
    fd-find \
    bat \
    # Network tools
    netcat-openbsd \
    iputils-ping \
    dnsutils \
    # Process management
    supervisor \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ============================================================================
# Node.js (for npm-based projects)
# ============================================================================

RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ============================================================================
# Google Chrome (for browser automation)
# ============================================================================

RUN wget -q -O /tmp/google-chrome-key.pub https://dl-ssl.google.com/linux/linux_signing_key.pub \
    && gpg --dearmor -o /usr/share/keyrings/google-chrome-keyring.gpg /tmp/google-chrome-key.pub \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/google-chrome-key.pub

# ============================================================================
# Playwright (browser automation)
# ============================================================================

RUN npm install -g playwright@latest \
    && playwright install --with-deps chromium firefox webkit

# Set Playwright to use the Chrome we installed
ENV PLAYWRIGHT_BROWSERS_PATH=/usr/lib/playwright

# ============================================================================
# GitHub CLI (for PR/issue management)
# ============================================================================

RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ============================================================================
# Docker CLI (for nested container scenarios)
# ============================================================================

RUN install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ============================================================================
# Additional Language Support (optional but useful)
# ============================================================================

# Python packages for common tasks + Prefect (for orchestration when used as work pool image)
RUN pip3 install --break-system-packages --no-cache-dir \
    pyyaml \
    requests \
    pytest \
    black \
    flake8 \
    mypy \
    prefect

# Go (for Go projects)
RUN wget https://go.dev/dl/go1.22.0.linux-amd64.tar.gz \
    && tar -C /usr/local -xzf go1.22.0.linux-amd64.tar.gz \
    && rm go1.22.0.linux-amd64.tar.gz

ENV PATH="/usr/local/go/bin:${PATH}"
ENV GOPATH="/go"
ENV PATH="${GOPATH}/bin:${PATH}"

# Rust (for Rust projects)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# ============================================================================
# Claude Code CLI
# ============================================================================

# Install Claude Code CLI
# Note: Replace with actual installation method once available
RUN curl -fsSL https://claude.ai/install.sh | bash || \
    echo "Claude Code CLI installation - update with actual method"

# ============================================================================
# Skill Runner Infrastructure
# ============================================================================

# Create directory structure
RUN mkdir -p /app/skills \
    /app/scripts \
    /input \
    /output \
    /workspace \
    /artifacts

# Copy skill definitions
COPY skills/*.yaml /app/skills/

# Copy entrypoint script
COPY scripts/skill-entrypoint.py /app/scripts/

# Make entrypoint executable
RUN chmod +x /app/scripts/skill-entrypoint.py

# ============================================================================
# Environment Configuration
# ============================================================================

# Set working directory
WORKDIR /workspace

# Git configuration (for commits)
RUN git config --global user.name "Claude Code Bot" \
    && git config --global user.email "claude-bot@anthropic.com" \
    && git config --global init.defaultBranch main

# Environment variables
ENV SKILL=""
ENV TASK_INPUT_PATH="/input/task-input.yaml"
ENV OUTPUT_PATH="/output"
ENV WORKSPACE_PATH="/workspace"
ENV ARTIFACTS_PATH="/artifacts"

# Claude API configuration
ENV ANTHROPIC_API_KEY=""
ENV CLAUDE_MODEL="claude-sonnet-4-5-20250929"

# Browser automation
ENV CHROME_BIN="/usr/bin/google-chrome-stable"
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

# ============================================================================
# Health Check
# ============================================================================

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD [ -f /tmp/skill-runner-healthy ] || exit 1

# ============================================================================
# Entrypoint
# ============================================================================

ENTRYPOINT ["/app/scripts/skill-entrypoint.py"]
CMD ["--help"]

# ============================================================================
# Metadata
# ============================================================================

LABEL org.opencontainers.image.title="Claude Code Skill Runner"
LABEL org.opencontainers.image.description="Unified container for all Claude Code CI/CD skills"
LABEL org.opencontainers.image.source="https://github.com/kruczele/claude-cicd"
LABEL org.opencontainers.image.licenses="MIT"
