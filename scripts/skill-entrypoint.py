#!/usr/bin/env python3
"""
Entrypoint script for Claude Code skill runner.
Loads the appropriate skill definition and executes it.

When used as Prefect work pool image, passes through to prefect (e.g. prefect flow-run execute).
"""

import os
import sys

# Pass-through for Prefect orchestration - worker runs "prefect flow-run execute ..."
if len(sys.argv) >= 2 and sys.argv[1] == "prefect":
    os.execv(sys.executable, [sys.executable, "-m", "prefect"] + sys.argv[2:])

import yaml
import json
import subprocess
from pathlib import Path
from typing import Dict, Any
import argparse


class SkillRunner:
    """Orchestrates Claude Code execution for a specific skill."""

    def __init__(self):
        self.task_input_path = Path(os.environ.get("TASK_INPUT_PATH", "/input/task-input.yaml"))
        self.output_path = Path(os.environ.get("OUTPUT_PATH", "/output"))
        self.workspace_path = Path(os.environ.get("WORKSPACE_PATH", "/workspace"))
        self.artifacts_path = Path(os.environ.get("ARTIFACTS_PATH", "/artifacts"))
        self.skills_path = Path("/app/skills")

    def load_task_input(self) -> Dict[str, Any]:
        """Load task input manifest."""
        if not self.task_input_path.exists():
            raise FileNotFoundError(f"Task input not found: {self.task_input_path}")

        with open(self.task_input_path) as f:
            return yaml.safe_load(f)

    def load_skill_definition(self, skill_name: str) -> Dict[str, Any]:
        """Load skill definition YAML."""
        skill_file = self.skills_path / f"{skill_name}.skill.yaml"

        if not skill_file.exists():
            raise FileNotFoundError(f"Skill definition not found: {skill_file}")

        with open(skill_file) as f:
            return yaml.safe_load(f)

    def prepare_claude_prompt(self, task_input: Dict, skill_def: Dict) -> str:
        """Build the complete prompt for Claude."""

        # Start with system prompt
        system_prompt = skill_def.get("prompts", {}).get("system", "")

        # Add task-specific prompt
        task_prompt = skill_def.get("prompts", {}).get("task", "")

        # Substitute variables in task prompt
        task_prompt = self.substitute_variables(task_prompt, task_input, skill_def)

        # Combine
        full_prompt = f"{system_prompt}\n\n---\n\n{task_prompt}"

        return full_prompt

    def substitute_variables(self, template: str, task_input: Dict, skill_def: Dict) -> str:
        """Replace {variable} placeholders in prompt template."""

        # Simple substitution for now - can be made more sophisticated
        result = template

        # Task fields
        if "task" in task_input:
            result = result.replace("{task.title}", task_input["task"].get("title", ""))
            result = result.replace("{task.description}", task_input["task"].get("description", ""))
            result = result.replace("{task.priority}", task_input["task"].get("priority", ""))

        # Git fields
        if "git" in task_input:
            result = result.replace("{git.target_branch}", task_input["git"].get("target_branch", ""))
            result = result.replace("{git.main_branch}", task_input["git"].get("main_branch", ""))

        # Context fields
        if "context" in task_input:
            result = result.replace("{context.working_directory}",
                                   task_input["context"].get("working_directory", ""))

        # Iteration
        result = result.replace("{iteration}", str(task_input.get("iteration", 1)))

        # Handle conditional blocks {if ...} {endif}
        # Simplified - just remove them for now
        import re
        result = re.sub(r'\{if [^}]+\}.*?\{endif\}', '', result, flags=re.DOTALL)

        return result

    def execute_claude(self, prompt: str, skill_name: str, task_input: Dict) -> Dict[str, Any]:
        """Execute Claude Code with the given prompt."""

        print(f"🤖 Executing skill: {skill_name}")
        print(f"📁 Workspace: {self.workspace_path}")
        print(f"📤 Output: {self.output_path}")

        # Change to workspace directory
        os.chdir(self.workspace_path)

        # Prepare Claude Code command
        # Note: Adjust based on actual Claude Code CLI interface
        claude_cmd = [
            "claude",
            "--prompt", prompt,
            "--workspace", str(self.workspace_path),
            "--output", str(self.output_path / "state.md"),
            "--model", os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5-20250929"),
        ]

        # Add any skill-specific flags
        if skill_name == "execute":
            claude_cmd.extend(["--allow-write", "--allow-git"])

        # Execute
        try:
            result = subprocess.run(
                claude_cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout
            )

            if result.returncode != 0:
                print(f"❌ Claude execution failed: {result.stderr}", file=sys.stderr)
                return {
                    "status": "error",
                    "error": result.stderr,
                    "stdout": result.stdout
                }

            print("✅ Claude execution completed")

            return {
                "status": "success",
                "stdout": result.stdout,
                "stderr": result.stderr
            }

        except subprocess.TimeoutExpired:
            print("⏱️  Claude execution timed out", file=sys.stderr)
            return {
                "status": "timeout",
                "error": "Execution exceeded 30 minute timeout"
            }
        except Exception as e:
            print(f"❌ Unexpected error: {e}", file=sys.stderr)
            return {
                "status": "error",
                "error": str(e)
            }

    def collect_outputs(self, skill_name: str) -> Dict[str, str]:
        """Collect output files generated by the skill."""

        outputs = {}

        # Expected output files based on skill
        output_files = {
            "triage": ["triage-plan.yaml", "feedback.md"],
            "execute": ["state.md", "feedback.md"],
            "pre-verify": ["validation-strategy.md"],
            "verify": ["verification-results.md"],
            "devils-advocate": ["assumption-analysis.md", "recommended-fix.md"]
        }

        for filename in output_files.get(skill_name, []):
            filepath = self.output_path / filename
            if filepath.exists():
                outputs[filename] = filepath.read_text()

        return outputs

    def create_execution_summary(self, task_input: Dict, skill_name: str,
                                 claude_result: Dict, outputs: Dict) -> Dict:
        """Create a summary of the execution."""

        return {
            "task_id": task_input.get("task_id"),
            "skill": skill_name,
            "iteration": task_input.get("iteration"),
            "status": claude_result.get("status"),
            "outputs": list(outputs.keys()),
            "workspace": str(self.workspace_path),
            "artifacts": str(self.artifacts_path)
        }

    def run(self, skill_name: str = None) -> int:
        """Main execution flow."""

        try:
            # Load task input
            print("📥 Loading task input...")
            task_input = self.load_task_input()

            # Determine skill (from env, task input, or CLI arg)
            if not skill_name:
                skill_name = os.environ.get("SKILL") or task_input.get("skill")

            if not skill_name:
                print("❌ No skill specified (use --skill or SKILL env var)", file=sys.stderr)
                return 1

            print(f"🎯 Skill: {skill_name}")

            # Load skill definition
            print("📚 Loading skill definition...")
            skill_def = self.load_skill_definition(skill_name)

            # Prepare prompt
            print("📝 Preparing Claude prompt...")
            prompt = self.prepare_claude_prompt(task_input, skill_def)

            # Execute Claude
            claude_result = self.execute_claude(prompt, skill_name, task_input)

            # Collect outputs
            print("📦 Collecting outputs...")
            outputs = self.collect_outputs(skill_name)

            # Create summary
            summary = self.create_execution_summary(task_input, skill_name, claude_result, outputs)

            # Write summary
            summary_path = self.output_path / "execution-summary.json"
            with open(summary_path, "w") as f:
                json.dump(summary, f, indent=2)

            print(f"📊 Summary written to {summary_path}")

            # Create health check marker
            Path("/tmp/skill-runner-healthy").touch()

            # Return exit code based on status
            if claude_result.get("status") == "success":
                print("✅ Skill execution successful")
                return 0
            else:
                print(f"❌ Skill execution failed: {claude_result.get('status')}", file=sys.stderr)
                return 1

        except Exception as e:
            print(f"💥 Fatal error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1


def main():
    parser = argparse.ArgumentParser(
        description="Claude Code Skill Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--skill",
        choices=["triage", "execute", "pre-verify", "verify", "devils-advocate"],
        help="Skill to execute (or set SKILL env var)"
    )

    parser.add_argument(
        "--task-input",
        type=Path,
        help="Path to task-input.yaml (or set TASK_INPUT_PATH env var)"
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Output directory (or set OUTPUT_PATH env var)"
    )

    parser.add_argument(
        "--workspace",
        type=Path,
        help="Workspace directory (or set WORKSPACE_PATH env var)"
    )

    args = parser.parse_args()

    # Override env vars with CLI args if provided
    if args.task_input:
        os.environ["TASK_INPUT_PATH"] = str(args.task_input)
    if args.output:
        os.environ["OUTPUT_PATH"] = str(args.output)
    if args.workspace:
        os.environ["WORKSPACE_PATH"] = str(args.workspace)

    runner = SkillRunner()
    sys.exit(runner.run(skill_name=args.skill))


if __name__ == "__main__":
    main()
