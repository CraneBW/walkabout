"""Subprocess entry point for walkthrough execution.

Usage: python runner.py --workspace NOTES_DIR --module my_note --output trace.json
"""
import argparse
import os, json, sys, os
from dataclasses import asdict

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True, help="Path to notes directory")
    parser.add_argument("--module", required=True, help="Module name to import")
    parser.add_argument("--output", required=True, help="Output trace JSON path")
    args = parser.parse_args()
    # Use workspace venv Python if available
    venv_python = os.path.join(args.workspace, ".venv", "bin", "python3")
    if not os.path.exists(venv_python):
        venv_python = os.path.join(os.path.expanduser("~/.walkabout"), ".venv", "bin", "python3")
    if os.path.exists(venv_python):
        # Re-exec self with venv Python
        if sys.executable != venv_python:
            os.execv(venv_python, [venv_python] + sys.argv)


    # Setup paths: workspace first, then core engine
    runner_dir = os.path.dirname(os.path.abspath(__file__))
    core_dir = os.path.join(runner_dir, 'core')  # walkabout/core/ — has execute_util, file_util, execute
    walkabout_root = os.path.join(runner_dir, '..')  # project root — has walkabout package
    sys.path.insert(0, args.workspace)
    sys.path.insert(0, core_dir)  # for execute_util, file_util, etc.
    sys.path.insert(0, walkabout_root)  # for walkabout.core
    os.environ["WALKABOUT_HOME"] = os.path.expanduser("~/.walkabout")
    os.chdir(args.workspace)

    # Import the module
    import importlib
    mod = importlib.import_module(args.module)

    # Execute with tracing
    # Import execute from walkabout.core
    from execute import execute

    trace = execute(module_name=args.module, inspect_all_variables=False)

    # Save trace
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(asdict(trace), f, indent=2)

    print(f"Trace saved: {args.output} ({len(trace.steps)} steps)", file=sys.stderr)


if __name__ == "__main__":
    main()
