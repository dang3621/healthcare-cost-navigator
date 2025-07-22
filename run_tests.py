#!/usr/bin/env python3
"""
Test runner script for healthcare-cost-navigator

This script provides convenient ways to run tests with different configurations.
"""
import subprocess
import sys
import argparse


def run_command(cmd):
    """Run a command and return the result"""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Run tests for healthcare-cost-navigator")
    parser.add_argument(
        "--coverage", 
        action="store_true", 
        help="Run tests with coverage report"
    )
    parser.add_argument(
        "--verbose", "-v", 
        action="store_true", 
        help="Run tests in verbose mode"
    )
    parser.add_argument(
        "--fast", 
        action="store_true", 
        help="Run only fast tests (exclude slow tests)"
    )
    parser.add_argument(
        "--integration", 
        action="store_true", 
        help="Run only integration tests"
    )
    parser.add_argument(
        "--unit", 
        action="store_true", 
        help="Run only unit tests"
    )
    parser.add_argument(
        "--file", 
        type=str, 
        help="Run tests from specific file"
    )
    parser.add_argument(
        "--test", 
        type=str, 
        help="Run specific test function"
    )
    
    args = parser.parse_args()
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add coverage if requested
    if args.coverage:
        cmd.extend(["--cov=app", "--cov-report=html", "--cov-report=term"])
    
    # Add verbosity
    if args.verbose:
        cmd.append("-v")
    
    # Filter tests by markers
    if args.fast:
        cmd.extend(["-m", "not slow"])
    elif args.integration:
        cmd.extend(["-m", "integration"])
    elif args.unit:
        cmd.extend(["-m", "unit"])
    
    # Run specific file or test
    if args.file:
        cmd.append(f"tests/{args.file}")
    elif args.test:
        cmd.extend(["-k", args.test])
    
    # Run the tests
    return run_command(cmd)


if __name__ == "__main__":
    sys.exit(main())
