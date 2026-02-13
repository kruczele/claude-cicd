"""
Prefect flows for orchestrating Claude Code skills in containers.
Provides resilient, resumable development workflow.
"""

from prefect import flow, task, get_run_logger
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule
import subprocess
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import time


# ============================================================================
# Container Execution
# ============================================================================

@task(retries=1, retry_delay_seconds=10)
def run_skill_in_container(
    skill_name: str,
    task_input_path: Path,
    workspace_path: Path,
    output_path: Path
) -> Dict[str, Any]:
    """
    Runs a Claude skill in an isolated Docker container.

    Args:
        skill_name: Name of skill (triage, execute, pre-verify, verify, devils-advocate)
        task_input_path: Path to task-input.yaml
        workspace_path: Path to code workspace
        output_path: Path where outputs will be written

    Returns:
        Dict with status, output files, and metadata
    """
    logger = get_run_logger()
    logger.info(f"Running skill '{skill_name}' in container")

    # Docker run command
    cmd = [
        "docker", "run",
        "--rm",
        "-v", f"{workspace_path}:/workspace",
        "-v", f"{task_input_path}:/input/task-input.yaml:ro",
        "-v", f"{output_path}:/output",
        "-e", f"SKILL={skill_name}",
        f"claude-skill-{skill_name}:latest"
    ]

    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    duration = time.time() - start_time

    if result.returncode != 0:
        logger.error(f"Skill failed: {result.stderr}")
        raise Exception(f"Skill {skill_name} failed with code {result.returncode}")

    # Parse outputs
    outputs = {}
    for output_file in output_path.glob("*.md"):
        outputs[output_file.stem] = output_file.read_text()

    for output_file in output_path.glob("*.yaml"):
        outputs[output_file.stem] = yaml.safe_load(output_file.read_text())

    logger.info(f"Skill completed in {duration:.1f}s")

    return {
        "status": "success",
        "duration_seconds": duration,
        "outputs": outputs,
        "skill": skill_name
    }


# ============================================================================
# Individual Skill Flows
# ============================================================================

@flow(name="triage-flow")
def triage_flow(task_id: str, task_input_path: Path) -> Dict[str, Any]:
    """
    Analyzes task and determines execution strategy.
    """
    logger = get_run_logger()
    logger.info(f"Triaging task {task_id}")

    workspace = Path("/workspace")
    output_path = Path(f"/artifacts/{task_id}/triage")
    output_path.mkdir(parents=True, exist_ok=True)

    result = run_skill_in_container(
        skill_name="triage",
        task_input_path=task_input_path,
        workspace_path=workspace,
        output_path=output_path
    )

    return result


@flow(name="execute-flow")
def execute_flow(
    task_id: str,
    task_input_path: Path,
    iteration: int = 1
) -> Dict[str, Any]:
    """
    Executes implementation work.
    """
    logger = get_run_logger()
    logger.info(f"Executing task {task_id} (iteration {iteration})")

    workspace = Path("/workspace")
    output_path = Path(f"/artifacts/{task_id}/execute/iter-{iteration}")
    output_path.mkdir(parents=True, exist_ok=True)

    result = run_skill_in_container(
        skill_name="execute",
        task_input_path=task_input_path,
        workspace_path=workspace,
        output_path=output_path
    )

    return result


@flow(name="pre-verify-flow")
def pre_verify_flow(task_id: str, state_path: Path) -> Dict[str, Any]:
    """
    Creates validation strategy.
    """
    logger = get_run_logger()
    logger.info(f"Creating validation strategy for task {task_id}")

    # Build task input with state
    task_input = yaml.safe_load(Path(f"/artifacts/{task_id}/task-input.yaml").read_text())
    task_input["context"]["previous_state_path"] = str(state_path)

    temp_input = Path(f"/tmp/{task_id}-preverify-input.yaml")
    temp_input.write_text(yaml.dump(task_input))

    workspace = Path("/workspace")
    output_path = Path(f"/artifacts/{task_id}/pre-verify")
    output_path.mkdir(parents=True, exist_ok=True)

    result = run_skill_in_container(
        skill_name="pre-verify",
        task_input_path=temp_input,
        workspace_path=workspace,
        output_path=output_path
    )

    return result


@flow(name="verify-flow")
def verify_flow(
    task_id: str,
    validation_strategy_path: Path,
    attempt_number: int = 1
) -> Dict[str, Any]:
    """
    Executes validation strategy.
    """
    logger = get_run_logger()
    logger.info(f"Verifying task {task_id} (attempt {attempt_number})")

    # Build task input with strategy
    task_input = yaml.safe_load(Path(f"/artifacts/{task_id}/task-input.yaml").read_text())
    task_input["context"]["validation_strategy_path"] = str(validation_strategy_path)
    task_input["iteration"] = attempt_number

    temp_input = Path(f"/tmp/{task_id}-verify-input.yaml")
    temp_input.write_text(yaml.dump(task_input))

    workspace = Path("/workspace")
    output_path = Path(f"/artifacts/{task_id}/verify/attempt-{attempt_number}")
    output_path.mkdir(parents=True, exist_ok=True)

    result = run_skill_in_container(
        skill_name="verify",
        task_input_path=temp_input,
        workspace_path=workspace,
        output_path=output_path
    )

    return result


@flow(name="devils-advocate-flow")
def devils_advocate_flow(task_id: str, verification_history_path: Path) -> Dict[str, Any]:
    """
    Performs meta-analysis of repeated failures.
    """
    logger = get_run_logger()
    logger.info(f"Running devils-advocate analysis for task {task_id}")

    # Build task input with full history
    task_input = yaml.safe_load(Path(f"/artifacts/{task_id}/task-input.yaml").read_text())
    task_input["context"]["verification_history_path"] = str(verification_history_path)

    temp_input = Path(f"/tmp/{task_id}-devilsadvocate-input.yaml")
    temp_input.write_text(yaml.dump(task_input))

    workspace = Path("/workspace")
    output_path = Path(f"/artifacts/{task_id}/devils-advocate")
    output_path.mkdir(parents=True, exist_ok=True)

    result = run_skill_in_container(
        skill_name="devils-advocate",
        task_input_path=temp_input,
        workspace_path=workspace,
        output_path=output_path
    )

    return result


# ============================================================================
# Main Development Cycle Flow
# ============================================================================

@flow(name="development-cycle", log_prints=True)
def development_cycle(
    task_id: str,
    task_title: str,
    task_description: str,
    target_branch: str,
    priority: str = "medium"
) -> str:
    """
    Complete development cycle: triage → execute → verify loop → PR.

    This is the main orchestration flow that coordinates all skills.
    Handles the full lifecycle including verification loops and
    devils-advocate triggering.

    Returns:
        Status: "completed", "awaiting_user_input", "failed", "escalated"
    """
    logger = get_run_logger()
    logger.info(f"Starting development cycle for task '{task_title}'")

    # Create task input manifest
    artifacts_base = Path(f"/artifacts/{task_id}")
    artifacts_base.mkdir(parents=True, exist_ok=True)

    task_input = {
        "task_id": task_id,
        "iteration": 1,
        "parent_task_id": None,
        "skill": "triage",
        "git": {
            "target_branch": target_branch,
            "main_branch": "main"
        },
        "task": {
            "title": task_title,
            "description": task_description,
            "priority": priority,
            "labels": [],
            "estimated_complexity": "unknown"
        },
        "context": {
            "working_directory": "/workspace"
        },
        "metadata": {
            "created_at": time.time(),
            "triggered_by": "prefect"
        },
        "resources": {
            "skills_available": ["code_analysis", "testing", "git_operations"],
            "max_iterations": 10
        }
    }

    task_input_path = artifacts_base / "task-input.yaml"
    task_input_path.write_text(yaml.dump(task_input))

    # Step 1: Triage
    triage_result = triage_flow(task_id, task_input_path)

    # Check if triage needs user input
    if "feedback" in triage_result["outputs"]:
        logger.info("Triage requires user input")
        return "awaiting_user_input"

    triage_plan = triage_result["outputs"].get("triage-plan", {})

    # If trivial, execute immediately and return
    if triage_plan.get("decision") == "trivial":
        logger.info("Trivial task - executing immediately")
        execute_result = execute_flow(task_id, task_input_path, iteration=1)

        if execute_result["outputs"]["state"]["status"] == "completed":
            return "completed"

    # Step 2: Execute (iterative)
    iteration = 1
    max_iterations = 10

    while iteration <= max_iterations:
        logger.info(f"Execute iteration {iteration}")

        execute_result = execute_flow(task_id, task_input_path, iteration)
        state = execute_result["outputs"]["state"]

        # Check for user questions
        if "feedback" in execute_result["outputs"]:
            feedback = execute_result["outputs"]["feedback"]
            if feedback.get("has_blocking_questions"):
                logger.info("Execution blocked on user questions")
                return "awaiting_user_input"

        # Check if execution complete
        if state["status"] == "completed":
            logger.info("Execution completed - moving to verification")
            break

        # Check if we need another iteration
        if not state.get("next_iteration_needed"):
            logger.info("Execution stopped without completion")
            return "escalated"

        iteration += 1

    if iteration > max_iterations:
        logger.error("Max iterations exceeded")
        return "failed"

    # Step 3: Pre-verify
    state_path = artifacts_base / f"execute/iter-{iteration}" / "state.md"
    preverify_result = pre_verify_flow(task_id, state_path)

    validation_strategy_path = artifacts_base / "pre-verify" / "validation-strategy.md"

    # Step 4: Verification loop
    verify_attempt = 1
    max_verify_attempts = 5

    while verify_attempt <= max_verify_attempts:
        logger.info(f"Verification attempt {verify_attempt}")

        verify_result = verify_flow(task_id, validation_strategy_path, verify_attempt)
        verification = verify_result["outputs"]["verification-results"]

        if verification["status"] == "passed":
            logger.info("✅ Verification passed!")
            return "completed"

        # Check if we should trigger devils-advocate
        if verify_attempt >= 3 and verification.get("requires_devils_advocate"):
            logger.info("🤔 Triggering devils-advocate analysis")

            verification_history_path = artifacts_base / "verify"
            da_result = devils_advocate_flow(task_id, verification_history_path)

            analysis = da_result["outputs"]["assumption-analysis"]

            if analysis["root_cause_found"] and analysis["confidence"] >= 0.85:
                logger.info(f"Root cause found with {analysis['confidence']} confidence")

                # Could automatically apply fix here if confident
                if analysis.get("recommended_action") == "auto_fix":
                    logger.info("Applying automatic fix")
                    # Update task input with fix guidance
                    task_input["context"]["devils_advocate_analysis"] = str(
                        artifacts_base / "devils-advocate" / "assumption-analysis.md"
                    )
                    task_input_path.write_text(yaml.dump(task_input))

                    # Execute fix
                    fix_result = execute_flow(task_id, task_input_path, iteration + 1)
                    iteration += 1

                    # Re-verify
                    verify_attempt += 1
                    continue

            # If root cause unclear or needs user decision, escalate
            logger.info("Escalating to user for decision")
            return "awaiting_user_input"

        # Try fix and retry
        logger.info("Verification failed - will retry after fix")

        # Here you might trigger another execute iteration with the feedback
        # For now, just increment attempt
        verify_attempt += 1

    if verify_attempt > max_verify_attempts:
        logger.error("Max verification attempts exceeded")
        return "escalated"

    return "completed"


# ============================================================================
# User Feedback Flow
# ============================================================================

@flow(name="process-user-feedback")
def process_user_feedback(
    task_id: str,
    user_responses: Dict[str, str]
) -> str:
    """
    Processes user responses to feedback questions and resumes workflow.
    """
    logger = get_run_logger()
    logger.info(f"Processing user feedback for task {task_id}")

    # Save user responses
    artifacts_base = Path(f"/artifacts/{task_id}")
    responses_path = artifacts_base / "user-responses.md"

    # Format as markdown
    content = "# User Responses\n\n"
    for question, answer in user_responses.items():
        content += f"## {question}\n\n{answer}\n\n"

    responses_path.write_text(content)

    # Update task input with responses path
    task_input_path = artifacts_base / "task-input.yaml"
    task_input = yaml.safe_load(task_input_path.read_text())
    task_input["context"]["user_responses_path"] = str(responses_path)
    task_input_path.write_text(yaml.dump(task_input))

    # Resume development cycle
    return development_cycle(
        task_id=task_id,
        task_title=task_input["task"]["title"],
        task_description=task_input["task"]["description"],
        target_branch=task_input["git"]["target_branch"],
        priority=task_input["task"]["priority"]
    )


# ============================================================================
# Deployment
# ============================================================================

if __name__ == "__main__":
    # Create deployments for the flows

    deployment = Deployment.build_from_flow(
        flow=development_cycle,
        name="claude-dev-cycle",
        work_queue_name="claude-skills",
        parameters={
            "task_id": "task-example",
            "task_title": "Example Task",
            "task_description": "This is an example task",
            "target_branch": "feature/example",
            "priority": "medium"
        }
    )

    deployment.apply()

    print("✅ Prefect flows deployed")
    print("Start agent with: prefect agent start -q claude-skills")
