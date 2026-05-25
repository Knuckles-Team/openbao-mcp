import pytest

@pytest.fixture
def mock_ctx():
    class MockCtx:
        def info(self, msg): pass
        def warn(self, msg): pass
        def error(self, msg): pass
    return MockCtx()
