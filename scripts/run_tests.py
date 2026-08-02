#!/usr/bin/env python3
"""Test runner with detailed reporting."""

import sys
import subprocess
from pathlib import Path


def run_tests():
    """Run full test suite with reporting."""
    print("=" * 80)
    print("INSTA360-ANALYZER TEST SUITE")
    print("=" * 80)
    print()

    # Test categories
    test_suites = [
        {
            "name": "Unit Tests: Checkpoint Manager",
            "path": "tests/unit/test_checkpoint_manager.py",
            "description": "Atomic saves, loading, state tracking",
        },
        {
            "name": "Unit Tests: Recovery Manager",
            "path": "tests/unit/test_recovery.py",
            "description": "Recovery point detection, state restoration",
        },
        {
            "name": "Integration Tests: Stage 3 Analysis",
            "path": "tests/integration/test_stage3_analysis.py",
            "description": "Vision analysis, checkpointing, progress tracking",
        },
        {
            "name": "Integration Tests: Recovery Simulation",
            "path": "tests/integration/test_recovery_simulation.py",
            "description": "Failure scenarios, resume without duplication",
        },
    ]

    # Run pytest with verbose output
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-v",
        "--tb=short",
        "--color=yes",
        *[suite["path"] for suite in test_suites],
    ]

    print("Running pytest with detailed output...")
    print(f"Command: {' '.join(cmd)}")
    print()

    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
        return result.returncode

    except FileNotFoundError:
        print("❌ ERROR: pytest not installed")
        print("Install with: pip install -r requirements.txt")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
