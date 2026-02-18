# NovaSR Tests

## Running Tests

Install pytest first:
```bash
pip install pytest
```

Run all tests:
```bash
pytest tests/
```

Run with verbose output:
```bash
pytest tests/ -v
```

Run a specific test file:
```bash
pytest tests/test_basic.py
```

## Test Coverage

Currently includes:
- Import tests
- Audio loading helper tests
- GUI utility function tests

## Adding New Tests

1. Create a new file in `tests/` directory with prefix `test_`
2. Import pytest and the modules you want to test
3. Create test functions with prefix `test_`
4. Use assertions to verify expected behavior

Example:
```python
def test_my_feature():
    from NovaSR import FastSR
    # Test code here
    assert True
```

## Future Test Areas

- [ ] Model inference tests (with mock weights)
- [ ] Audio processing pipeline tests
- [ ] GUI integration tests
- [ ] Cross-platform compatibility tests
- [ ] Error handling tests
