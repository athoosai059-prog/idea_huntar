#!/usr/bin/env python3
"""
Test runner script for IdeaHunter.
Provides convenient commands for running different test suites.
"""

import subprocess
import sys
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and print results."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"{'='*60}\n")
    result = subprocess.run(cmd, shell=True)
    return result.returncode == 0


def run_all_tests():
    """Run all tests with coverage."""
    return run_command(
        "pytest tests/ -v --cov=backend --cov-report=html --cov-report=term-missing",
        "All tests with coverage"
    )


def run_unit_tests():
    """Run only unit tests."""
    return run_command(
        "pytest tests/ -v -m 'not integration' --cov=backend --cov-report=term-missing",
        "Unit tests only"
    )


def run_integration_tests():
    """Run only integration tests."""
    return run_command(
        "pytest tests/ -v -m integration --cov=backend --cov-report=term-missing",
        "Integration tests only"
    )


def run_database_tests():
    """Run database tests."""
    return run_command(
        "pytest tests/test_database.py -v --cov=backend.db --cov-report=term-missing",
        "Database tests"
    )


def run_api_tests():
    """Run API tests."""
    return run_command(
        "pytest tests/test_api.py -v --cov=backend.api --cov-report=term-missing",
        "API tests"
    )


def run_scraper_tests():
    """Run scraper tests."""
    return run_command(
        "pytest tests/test_scrapers.py -v --cov=backend.scrapers --cov-report=term-missing",
        "Scraper tests"
    )


def run_validator_tests():
    """Run validator tests."""
    return run_command(
        "pytest tests/test_validators.py -v --cov=backend.validators --cov-report=term-missing",
        "Validator tests"
    )


def run_fast_tests():
    """Run fast tests only (exclude slow tests)."""
    return run_command(
        "pytest tests/ -v -m 'not slow' --cov=backend --cov-report=term-missing",
        "Fast tests only"
    )


def run_specific_test(test_file):
    """Run a specific test file."""
    return run_command(
        f"pytest {test_file} -v --cov=backend --cov-report=term-missing",
        f"Specific test: {test_file}"
    )


def run_with_parallel():
    """Run tests in parallel."""
    return run_command(
        "pytest tests/ -v -n auto --cov=backend --cov-report=term-missing",
        "Parallel tests"
    )


def show_coverage_report():
    """Open HTML coverage report."""
    html_file = Path("htmlcov/index.html")
    if html_file.exists():
        import webbrowser
        webbrowser.open(str(html_file.absolute()))
        print(f"Opening coverage report: {html_file.absolute()}")
        return True
    else:
        print("Coverage report not found. Run tests first.")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="IdeaHunter Test Runner")
    parser.add_argument(
        'command',
        nargs='?',
        choices=['all', 'unit', 'integration', 'database', 'api', 'scrapers',
                 'validators', 'fast', 'parallel', 'coverage'],
        default='all',
        help='Test command to run'
    )
    parser.add_argument(
        '--file',
        help='Run specific test file'
    )

    args = parser.parse_args()

    # Change to project directory
    project_dir = Path(__file__).parent
    import os
    os.chdir(project_dir)

    # Run appropriate command
    success = False

    if args.file:
        success = run_specific_test(args.file)
    elif args.command == 'all':
        success = run_all_tests()
    elif args.command == 'unit':
        success = run_unit_tests()
    elif args.command == 'integration':
        success = run_integration_tests()
    elif args.command == 'database':
        success = run_database_tests()
    elif args.command == 'api':
        success = run_api_tests()
    elif args.command == 'scrapers':
        success = run_scraper_tests()
    elif args.command == 'validators':
        success = run_validator_tests()
    elif args.command == 'fast':
        success = run_fast_tests()
    elif args.command == 'parallel':
        success = run_with_parallel()
    elif args.command == 'coverage':
        success = show_coverage_report()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()