"""Test runner script for the ecommerce analytics project.

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py unit         # Run only unit tests
    python run_tests.py integration  # Run only integration tests
    python run_tests.py --coverage   # Run with coverage report
"""
import argparse
import sys
from pathlib import Path

from settings import configure_logging


def main():
    parser = argparse.ArgumentParser(description="Run tests for ecommerce analytics")
    parser.add_argument(
        "suite",
        nargs="?",
        choices=["all", "unit", "integration", "fast"],
        default="all",
        help="Test suite to run (default: all)",
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--file",
        help="Run specific test file",
    )
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = "DEBUG" if args.debug else "INFO"
    configure_logging(level=log_level, log_file="logs/test_run.log")
    
    # Build pytest command
    pytest_args = ["pytest"]
    
    # Add verbosity
    if args.verbose:
        pytest_args.append("-vv")
    else:
        pytest_args.append("-v")
    
    # Add coverage
    if args.coverage:
        pytest_args.extend(["--cov=.", "--cov-report=html", "--cov-report=term-missing"])
    
    # Add test selection
    if args.file:
        pytest_args.append(args.file)
    elif args.suite == "unit":
        pytest_args.extend(["-m", "unit", "tests/"])
    elif args.suite == "integration":
        pytest_args.extend(["-m", "integration", "tests/"])
    elif args.suite == "fast":
        pytest_args.extend(["-m", "not slow", "tests/"])
    else:
        pytest_args.append("tests/")
    
    # Run pytest
    import subprocess
    
    print(f"Running: {' '.join(pytest_args)}")
    print("-" * 80)
    
    result = subprocess.run(pytest_args)
    
    if result.returncode == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code {result.returncode}")
    
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
