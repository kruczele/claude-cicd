# Resilient Claude Code CI/CD System

A containerized, stateless workflow system for resilient Claude Code collaboration that survives process interruptions.

## 🎯 Problem Statement

Claude Code process terminations cause loss of work and context. This system provides:
- **Resilience**: Each iteration is self-contained and resumable
- **State persistence**: All state externalized to git and artifacts
- **Horizontal scalability**: Can run on different VMs across iterations
- **Clear contracts**: Well-defined inputs/outputs between stages

## 🏗️ Architecture

```
┌─────────────┐
│   User      │
│  Request    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────┐
│                  Prefect Orchestration               │
│                                                      │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐       │
│  │ Triage   │──▶│ Execute  │──▶│ Verify   │       │
│  │  Flow    │   │   Flow   │   │   Loop   │       │
│  └──────────┘   └─────┬────┘   └────┬─────┘       │
│                       │              │             │
│                       │    ┌─────────▼─────────┐   │
│                       │    │   Pre-Verify      │   │
│                       │    │   Flow            │   │
│                       │    └─────────┬─────────┘   │
│                       │              │             │
│                       │    ┌─────────▼─────────┐   │
│                       │    │   Verify          │   │
│                       │    │   Flow            │   │
│                       │    └─────────┬─────────┘   │
│                       │              │             │
│                       │         [Failed 3x?]       │
│                       │              │             │
│                       │    ┌─────────▼─────────┐   │
│                       └───▶│ Devils-Advocate   │   │
│                            │   Flow            │   │
│                            └───────────────────┘   │
└─────────────────────────────────────────────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │   Artifacts    │
                    │   - state.md   │
                    │   - feedback.md│
                    │   - results.md │
                    └────────────────┘
```

## 📦 Components

### Skills (Containerized Agents)

Each skill runs in an isolated Docker container with defined inputs/outputs:

1. **Triage** - Analyzes task, determines granularity
   - Input: `task-input.yaml`
   - Output: `triage-plan.yaml`, `feedback.md` (optional)

2. **Execute** - Implements code changes
   - Input: `task-input.yaml`, `state.md` (resume), `user-responses.md` (optional)
   - Output: `state.md`, `feedback.md` (optional), git commits

3. **Pre-Verify** - Creates validation strategy
   - Input: `task-input.yaml`, `state.md`, git commits
   - Output: `validation-strategy.md`

4. **Verify** - Executes validation tests
   - Input: `task-input.yaml`, `validation-strategy.md`
   - Output: `verification-results.md`, test artifacts

5. **Devils-Advocate** - Meta-analysis of repeated failures
   - Input: `task-input.yaml`, verification history
   - Output: `assumption-analysis.md`, `recommended-fix.md`

### Schemas

Data contracts between skills (YAML frontmatter + Markdown body):

- `task-input.schema.yaml` - Task definition and context
- `state-output.schema.yaml` - Execution state
- `feedback-output.schema.yaml` - Questions for user
- `validation-strategy.schema.yaml` - Test plan
- `verification-results.schema.yaml` - Test results
- `assumption-analysis.schema.yaml` - Root cause analysis

### Orchestration

Prefect flows coordinate skill execution:
- Parallel execution where possible
- Automatic retry logic
- State persistence
- User feedback loops
- Circuit breakers

## 🚀 Quick Start

### 1. Build Docker Images

```bash
# Build all skill containers
./scripts/build-containers.sh
```

### 2. Start Prefect

```bash
# Start Prefect server
prefect server start

# In another terminal, start agent
prefect agent start -q claude-skills
```

### 3. Deploy Flows

```bash
python orchestration/prefect_flows.py
```

### 4. Submit a Task

```bash
# Via CLI
./scripts/submit-task.sh \
  --title "Implement user authentication" \
  --description "Add JWT-based auth to the API" \
  --branch "feature/auth" \
  --priority "high"

# Or via Python API
from orchestration.prefect_flows import development_cycle

result = development_cycle(
    task_id="task-001",
    task_title="Implement user authentication",
    task_description="Add JWT-based auth to the API",
    target_branch="feature/auth",
    priority="high"
)
```

### 5. Monitor Progress

```bash
# Via Prefect UI
open http://localhost:4200

# Or via CLI
prefect flow-run ls
prefect flow-run inspect <flow-run-id>
```

### 6. Respond to Feedback

When Claude needs input, you'll see feedback in `/artifacts/{task-id}/feedback.md`:

```bash
# Review questions
cat /artifacts/task-001/feedback.md

# Submit responses via WebUI or CLI
./scripts/submit-feedback.sh task-001 \
  --q1 "Use PostgreSQL for refresh token storage" \
  --q2 "Defer password reset to separate task"
```

## 📁 Directory Structure

```
cicd/
├── schemas/                    # Data contracts
│   ├── task-input.schema.yaml
│   ├── state-output.schema.yaml
│   ├── feedback-output.schema.yaml
│   ├── validation-strategy.schema.yaml
│   ├── verification-results.schema.yaml
│   └── assumption-analysis.schema.yaml
│
├── skills/                     # Skill definitions
│   ├── triage.skill.yaml
│   ├── execute.skill.yaml
│   ├── pre-verify.skill.yaml
│   ├── verify.skill.yaml
│   └── devils-advocate.skill.yaml
│
├── orchestration/             # Prefect flows
│   ├── prefect_flows.py
│   └── flow_config.yaml
│
├── docker/                    # Container definitions
│   ├── Dockerfile.triage
│   ├── Dockerfile.execute
│   ├── Dockerfile.pre-verify
│   ├── Dockerfile.verify
│   └── Dockerfile.devils-advocate
│
├── scripts/                   # Utility scripts
│   ├── build-containers.sh
│   ├── submit-task.sh
│   └── submit-feedback.sh
│
└── webui/                     # Web interface (optional)
    ├── app.py
    └── templates/
```

## 🔄 Workflow Examples

### Example 1: Simple Task (Success Path)

```
User: "Fix typo in README"
  ↓
Triage: "trivial - execute immediately"
  ↓
Execute: Fix typo, commit
  ↓
Pre-Verify: "smoke tests only"
  ↓
Verify: ✅ All passed
  ↓
Result: PR created
```

### Example 2: Complex Task with Questions

```
User: "Add caching to API"
  ↓
Triage: "clarification_needed"
  ↓
Feedback: "Which cache? Redis/Memcached/In-memory?"
  ↓
[USER RESPONDS: "Redis"]
  ↓
Execute: Implement Redis caching
  ↓
Pre-Verify: "full validation + performance"
  ↓
Verify: ✅ All passed
  ↓
Result: PR created
```

### Example 3: Verification Loop with Devils-Advocate

```
User: "Implement token refresh"
  ↓
Triage: "medium complexity"
  ↓
Execute: Implement refresh endpoint
  ↓
Pre-Verify: "integration tests required"
  ↓
Verify (attempt 1): ❌ 401 errors
  ↓
Execute: Fix token persistence
  ↓
Verify (attempt 2): ❌ Still 401
  ↓
Execute: Fix middleware
  ↓
Verify (attempt 3): ❌ Still 401
  ↓
Devils-Advocate: "Type mismatch - string vs int userId"
  ↓
Execute: Remove .toString()
  ↓
Verify (attempt 4): ✅ Passed
  ↓
Result: PR created
```

## 📊 Key Features

### Resilience
- Each iteration can run on a different VM
- State persisted to disk/git between iterations
- Process can be killed and resumed without losing work

### Observability
- Complete audit trail in artifacts
- State documents show decision history
- Feedback documents capture all questions

### Intelligence
- Devils-advocate detects assumption violations
- Pattern recognition across verification attempts
- Root cause analysis when fixes aren't working

### Flexibility
- Granularity determined automatically
- User can provide input at any stage
- Can pause/resume at any point

## 🛠️ Next Steps

To implement this system:

1. **Create Dockerfiles** for each skill
2. **Implement skill entry points** (Python scripts that run Claude)
3. **Set up Prefect server** and deploy flows
4. **Build WebUI** for task submission and monitoring
5. **Test end-to-end** with real tasks
6. **Add CI/CD integration**

## 📝 Notes

**Schema Files**: The current schema files in `/schemas` have YAML parsing issues because they mix YAML frontmatter with Markdown content. These should be refactored to either:
- Pure documentation (Markdown files explaining the schema)
- JSON Schema definitions
- Example output files

The actual output files produced by skills will use the YAML frontmatter + Markdown body format correctly.

---

**Status**: 🏗️ Architecture Defined - Ready for Implementation

See the individual skill definitions in `/skills/` and orchestration code in `/orchestration/` for detailed specifications.
