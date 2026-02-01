#!/bin/bash
# Test runner script for Real Estate Tracker API

cd "$(dirname "$0")"

echo "========================================"
echo "Real Estate Tracker API - Test Suite"
echo "========================================"
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "Error: pytest not found. Installing test dependencies..."
    pip install -r requirements.txt
fi

# Parse arguments
TEST_TYPE="all"
VERBOSE="-v"

while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            TEST_TYPE="unit"
            shift
            ;;
        --integration)
            TEST_TYPE="integration"
            shift
            ;;
        --quick)
            TEST_TYPE="quick"
            shift
            ;;
        --verbose)
            VERBOSE="-vv"
            shift
            ;;
        --quiet)
            VERBOSE="-q"
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --unit          Run only unit tests (excludes integration)"
            echo "  --integration   Run only integration tests"
            echo "  --quick         Run quick tests only (excludes slow tests)"
            echo "  --verbose       Show verbose output (-vv)"
            echo "  --quiet         Show minimal output (-q)"
            echo "  --help          Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Run all tests"
            echo "  $0 --unit            # Run unit tests only"
            echo "  $0 --quick           # Run quick tests"
            echo "  $0 --verbose         # Run with verbose output"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Build pytest arguments
PYTEST_ARGS="$VERBOSE"

case $TEST_TYPE in
    unit)
        echo "Running unit tests only..."
        PYTEST_ARGS="$PYTEST_ARGS -m 'not integration'"
        ;;
    integration)
        echo "Running integration tests only..."
        PYTEST_ARGS="$PYTEST_ARGS tests/integration/"
        ;;
    quick)
        echo "Running quick tests (excluding slow)..."
        PYTEST_ARGS="$PYTEST_ARGS -m 'not slow'"
        ;;
    all)
        echo "Running all tests..."
        ;;
esac

echo ""
echo "Pytest arguments: $PYTEST_ARGS"
echo ""

# Run tests
eval "python -m pytest $PYTEST_ARGS"

EXIT_CODE=$?

echo ""
echo "========================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ All tests passed!"
else
    echo "✗ Some tests failed (exit code: $EXIT_CODE)"
fi
echo "========================================"

exit $EXIT_CODE
