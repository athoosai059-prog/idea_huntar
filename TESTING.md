# Testing Guide for IdeaHunter

This guide covers the comprehensive testing setup for the IdeaHunter project.

## Overview

The IdeaHunter project includes a complete testing suite with:
- **Unit tests**: Individual component testing
- **Integration tests**: End-to-end pipeline testing
- **API tests**: REST API endpoint testing
- **Scraper tests**: Data collection testing
- **Validator tests**: Data validation testing
- **Database tests**: Data persistence testing

## Test Structure

```
tests/
├── test_database.py      # Database function tests
├── test_api.py          # API route tests
├── test_scrapers.py     # Scraper tests
├── test_validators.py   # Validator tests
└── test_integration.py  # Integration tests
```

## Installation

Install testing dependencies:

```bash
pip install -r requirements.txt
```

## Running Tests

### Run All Tests

```bash
# Using pytest directly
pytest tests/ -v

# Using the test runner
python run_tests.py all
```

### Run Specific Test Suites

```bash
# Unit tests only
python run_tests.py unit

# Integration tests only
python run_tests.py integration

# Database tests
python run_tests.py database

# API tests
python run_tests.py api

# Scraper tests
python run_tests.py scrapers

# Validator tests
python run_tests.py validators
```

### Run Specific Test File

```bash
# Using pytest
pytest tests/test_database.py -v

# Using test runner
python run_tests.py --file tests/test_database.py
```

### Run Fast Tests Only

```bash
# Exclude slow tests
python run_tests.py fast
```

### Run Tests in Parallel

```bash
# Use multiple CPU cores
python run_tests.py parallel
```

## Coverage

### Generate Coverage Report

```bash
# HTML and terminal coverage
pytest tests/ --cov=backend --cov-report=html --cov-report=term-missing

# Using test runner
python run_tests.py all
```

### View Coverage Report

```bash
# Open HTML report in browser
python run_tests.py coverage

# Or manually open
open htmlcov/index.html  # macOS
start htmlcov/index.html # Windows
xdg-open htmlcov/index.html # Linux
```

## Test Configuration

The `pytest.ini` file contains pytest configuration:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

addopts =
    -v
    --strict-markers
    --tb=short
    --disable-warnings
    --cov=backend
    --cov-report=html
    --cov-report=term-missing
```

## Test Markers

Tests can be marked with specific markers:

- `@pytest.mark.slow` - Slow tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.api` - API tests
- `@pytest.mark.scraper` - Scraper tests
- `@pytest.mark.database` - Database tests

### Running by Marker

```bash
# Run only slow tests
pytest tests/ -v -m slow

# Run only integration tests
pytest tests/ -v -m integration

# Exclude slow tests
pytest tests/ -v -m "not slow"
```

## Writing Tests

### Basic Test Structure

```python
import pytest
from backend.db.database import save_ideas, get_all_ideas

def test_save_and_get_ideas():
    """Test saving and retrieving ideas."""
    ideas = [
        {
            "name": "Test Idea",
            "description": "Test description",
            "pain_point": "Test pain point",
            "source": "reddit",
            "keywords": ["test"],
            "score_overall": 8.0,
            "score_demand": 80,
            "score_competition": 30,
            "score_trend": 70,
            "score_uniqueness": 60
        }
    ]

    save_ideas(ideas)
    retrieved = get_all_ideas(min_score=0.0)

    assert len(retrieved) == 1
    assert retrieved[0]['name'] == 'Test Idea'
```

### Using Fixtures

```python
@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    import backend.db.database as db_module
    original_db_path = db_module.DB_PATH
    db_module.DB_PATH = Path(db_path)

    init_db()

    yield db_path

    os.unlink(db_path)
    db_module.DB_PATH = original_db_path

def test_with_fixture(temp_db):
    """Test using temporary database fixture."""
    # Test code here
    pass
```

### Mocking External Dependencies

```python
from unittest.mock import Mock, patch

@patch('backend.scrapers.reddit_scraper.requests.get')
def test_reddit_scraper(mock_get):
    """Test Reddit scraper with mocked requests."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'data': {'children': []}}
    mock_get.return_value = mock_response

    # Test code here
    pass
```

## Test Coverage Goals

Aim for:
- **Overall coverage**: >80%
- **Critical paths**: >90%
- **Database functions**: >85%
- **API routes**: >85%
- **Validators**: >80%

## Continuous Integration

The test suite is designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest tests/ -v --cov=backend --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

## Troubleshooting

### Import Errors

If you get import errors, ensure the backend directory is in your Python path:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

### Database Lock Errors

If you encounter database lock errors, ensure each test uses a temporary database:

```python
@pytest.fixture
def temp_db():
    fd, db_path = tempfile.mkstemp(suffix='.db')
    # ... setup and cleanup
```

### Slow Tests

If tests are running slowly, try:
1. Running tests in parallel: `pytest -n auto`
2. Excluding slow tests: `pytest -m "not slow"`
3. Using faster database: PostgreSQL instead of SQLite

## Best Practices

1. **Test isolation**: Each test should be independent
2. **Use fixtures**: For common setup/teardown logic
3. **Mock external services**: Don't make real API calls in tests
4. **Test edge cases**: Include invalid inputs and error conditions
5. **Keep tests fast**: Avoid unnecessary delays
6. **Descriptive names**: Use clear test function names
7. **Arrange-Act-Assert**: Structure tests clearly
8. **One assertion per test**: Keep tests focused

## Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Ensure all tests pass
3. Maintain or improve coverage
4. Update this guide if needed

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Coverage Plugin](https://pytest-cov.readthedocs.io/)
- [Python Testing Best Practices](https://docs.python-guide.org/writing/tests/)