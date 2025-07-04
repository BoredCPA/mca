#!/usr/bin/env python
"""
Test runner script for MCA CRM application
Provides convenient test execution with various options
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd):
    """Execute command and return result"""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description='Run MCA CRM tests')
    parser.add_argument(
        'test_type',
        nargs='?',
        default='all',
        choices=['all', 'unit', 'integration', 'e2e', 'models', 'schemas', 'crud', 'api'],
        help='Type of tests to run'
    )
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-x', '--exitfirst', action='store_true', help='Exit on first failure')
    parser.add_argument('-s', '--stdout', action='store_true', help='Show print statements')
    parser.add_argument('--cov', action='store_true', help='Generate coverage report')
    parser.add_argument('-k', '--keyword', help='Run tests matching keyword')
    parser.add_argument('--html', action='store_true', help='Generate HTML report')

    args = parser.parse_args()

    # Base pytest command
    cmd = ['pytest']

    # Add test directory based on type
    test_paths = {
        'all': 'tests/',
        'unit': 'tests/unit/',
        'integration': 'tests/integration/',
        'e2e': 'tests/e2e/',
        'models': 'tests/unit/test_models/',
        'schemas': 'tests/unit/test_schemas/',
        'crud': 'tests/unit/test_crud/',
        'api': 'tests/integration/test_routes/'
    }

    cmd.append(test_paths.get(args.test_type, 'tests/'))

    # Add options
    if args.verbose:
        cmd.append('-vv')

    if args.exitfirst:
        cmd.append('-x')

    if args.stdout:
        cmd.append('-s')

    if args.keyword:
        cmd.extend(['-k', args.keyword])

    if args.cov:
        cmd.extend(['--cov=app', '--cov-report=term-missing'])
        if args.html:
            cmd.append('--cov-report=html')

    if args.html and not args.cov:
        cmd.append('--html=test-report.html')
        cmd.append('--self-contained-html')

    # Run tests
    print(f"\nRunning {args.test_type} tests...\n")
    return_code = run_command(cmd)

    if return_code == 0:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")

    return return_code


if __name__ == '__main__':
    sys.exit(main())