# Real Estate Tracker API - Tests

## Test Structure

```
tests/
├── conftest.py              # Test fixtures and configuration
├── api/                     # API endpoint tests
│   ├── test_listings.py     # Listing endpoints
│   ├── test_historical_sales.py  # Historical sales endpoints
│   ├── test_analytics.py    # Analytics endpoints
│   └── test_photos.py       # Photo management endpoints
├── services/                # Service layer tests
│   ├── test_listing_service.py
│   └── test_photo_service.py
└── integration/             # Integration tests
    └── test_full_workflow.py
```

## Running Tests

### Run all tests
```bash
./run_tests.sh
```

### Run only unit tests
```bash
./run_tests.sh --unit
```

### Run only integration tests
```bash
./run_tests.sh --integration
```

### Run quick tests (skip slow tests)
```bash
./run_tests.sh --quick
```

### Run with verbose output
```bash
./run_tests.sh --verbose
```

### Run specific test file
```bash
python -m pytest tests/api/test_listings.py -v
```

### Run specific test
```bash
python -m pytest tests/api/test_listings.py::TestCreateListing::test_create_new_listing_success -v
```

## Test Fixtures

The `conftest.py` file provides these fixtures:

- `test_db` - In-memory SQLite database with schema
- `client` - FastAPI test client with mocked dependencies
- `auth_headers` - Authentication headers for API requests
- `sample_listing_data` - Sample listing data for tests
- `sample_historical_sale_data` - Sample historical sale data
- `create_listing` - Helper to create listings in tests
- `populated_db` - Database with multiple listings
- `temp_photo_dir` - Temporary directory for photo tests

## Writing Tests

### API Test Example
```python
def test_create_listing_success(client, auth_headers, sample_listing_data):
    response = client.post(
        "/api/v1/listings",
        json=sample_listing_data,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["is_new"] is True
```

### Service Test Example
```python
def test_create_new_listing(service):
    data = {
        "mls_number": "R1234567",
        "building_name": "Test Building",
        "price": 500000,
        "source_platform": "Test"
    }
    
    result = service.create_or_update_listing(data)
    
    assert result["success"] is True
    assert result["is_new"] is True
```

## Test Markers

- `@pytest.mark.slow` - Tests that take longer to run
- `@pytest.mark.integration` - Integration tests

Skip slow tests:
```bash
python -m pytest -m "not slow"
```

Run only integration tests:
```bash
python -m pytest -m integration
```

## Coverage

To run tests with coverage:
```bash
pip install pytest-cov
python -m pytest --cov=app --cov-report=html
```

View coverage report:
```bash
open htmlcov/index.html
```
