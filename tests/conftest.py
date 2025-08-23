"""
Shared pytest fixtures and configuration for all tests.
"""

import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator, List
from unittest.mock import MagicMock, Mock, patch

import pytest
from pydantic import BaseModel


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_file(temp_dir: Path) -> Generator[Path, None, None]:
    """Create a temporary file for testing."""
    temp_file_path = temp_dir / "test_file.txt"
    temp_file_path.write_text("test content")
    yield temp_file_path


@pytest.fixture
def mock_config() -> Dict[str, Any]:
    """Provide a mock configuration dictionary."""
    return {
        "api_key": "test-api-key",
        "api_url": "https://api.example.com",
        "timeout": 30,
        "retry_count": 3,
        "debug": True,
        "log_level": "DEBUG",
        "cache_enabled": False,
        "max_connections": 10,
    }


@pytest.fixture
def mock_env_vars(monkeypatch) -> Dict[str, str]:
    """Set up mock environment variables for testing."""
    env_vars = {
        "API_KEY": "test-api-key",
        "API_URL": "https://api.example.com",
        "DEBUG": "true",
        "LOG_LEVEL": "DEBUG",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client for testing API calls."""
    client = MagicMock()
    client.get = MagicMock(return_value={"status": "success", "data": []})
    client.post = MagicMock(return_value={"status": "created", "id": 123})
    client.put = MagicMock(return_value={"status": "updated"})
    client.delete = MagicMock(return_value={"status": "deleted"})
    return client


@pytest.fixture
def mock_async_http_client():
    """Create a mock async HTTP client for testing async API calls."""
    client = MagicMock()
    
    async def async_get(*args, **kwargs):
        return {"status": "success", "data": []}
    
    async def async_post(*args, **kwargs):
        return {"status": "created", "id": 123}
    
    async def async_put(*args, **kwargs):
        return {"status": "updated"}
    
    async def async_delete(*args, **kwargs):
        return {"status": "deleted"}
    
    client.get = MagicMock(side_effect=async_get)
    client.post = MagicMock(side_effect=async_post)
    client.put = MagicMock(side_effect=async_put)
    client.delete = MagicMock(side_effect=async_delete)
    return client


@pytest.fixture
def sample_json_data() -> Dict[str, Any]:
    """Provide sample JSON data for testing."""
    return {
        "id": 1,
        "name": "Test Item",
        "description": "A test item for unit testing",
        "attributes": {
            "color": "blue",
            "size": "medium",
            "weight": 1.5,
        },
        "tags": ["test", "sample", "fixture"],
        "active": True,
    }


@pytest.fixture
def sample_json_file(temp_dir: Path, sample_json_data: Dict[str, Any]) -> Path:
    """Create a temporary JSON file with sample data."""
    json_file = temp_dir / "sample.json"
    with open(json_file, "w") as f:
        json.dump(sample_json_data, f, indent=2)
    return json_file


@pytest.fixture
def mock_database_connection():
    """Create a mock database connection for testing."""
    connection = MagicMock()
    cursor = MagicMock()
    cursor.execute = MagicMock()
    cursor.fetchall = MagicMock(return_value=[])
    cursor.fetchone = MagicMock(return_value=None)
    connection.cursor = MagicMock(return_value=cursor)
    connection.commit = MagicMock()
    connection.rollback = MagicMock()
    connection.close = MagicMock()
    return connection


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client for testing AI/ML integrations."""
    client = MagicMock()
    client.generate = MagicMock(
        return_value={
            "response": "This is a generated response",
            "tokens": 42,
            "model": "test-model",
        }
    )
    client.embed = MagicMock(
        return_value={
            "embedding": [0.1, 0.2, 0.3, 0.4, 0.5],
            "dimensions": 5,
        }
    )
    return client


@pytest.fixture
def mock_async_llm_client():
    """Create a mock async LLM client for testing async AI/ML integrations."""
    client = MagicMock()
    
    async def async_generate(*args, **kwargs):
        return {
            "response": "This is an async generated response",
            "tokens": 42,
            "model": "test-model",
        }
    
    async def async_embed(*args, **kwargs):
        return {
            "embedding": [0.1, 0.2, 0.3, 0.4, 0.5],
            "dimensions": 5,
        }
    
    client.generate = MagicMock(side_effect=async_generate)
    client.embed = MagicMock(side_effect=async_embed)
    return client


@pytest.fixture
def mock_cache():
    """Create a mock cache for testing caching functionality."""
    cache_data = {}
    
    cache = MagicMock()
    cache.get = MagicMock(side_effect=lambda key: cache_data.get(key))
    cache.set = MagicMock(side_effect=lambda key, value: cache_data.update({key: value}))
    cache.delete = MagicMock(side_effect=lambda key: cache_data.pop(key, None))
    cache.clear = MagicMock(side_effect=cache_data.clear)
    cache.exists = MagicMock(side_effect=lambda key: key in cache_data)
    
    return cache


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing logging functionality."""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.critical = MagicMock()
    logger.exception = MagicMock()
    return logger


@pytest.fixture
def sample_pydantic_model():
    """Create a sample Pydantic model for testing."""
    class SampleModel(BaseModel):
        id: int
        name: str
        description: str = ""
        active: bool = True
        tags: List[str] = []
        metadata: Dict[str, Any] = {}
    
    return SampleModel(
        id=1,
        name="Test Model",
        description="A sample model for testing",
        tags=["test", "sample"],
        metadata={"created": "2024-01-01", "version": "1.0.0"},
    )


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection for testing real-time features."""
    ws = MagicMock()
    ws.send = MagicMock()
    ws.receive = MagicMock(return_value={"type": "message", "data": "test message"})
    ws.close = MagicMock()
    ws.ping = MagicMock()
    ws.pong = MagicMock()
    return ws


@pytest.fixture
def mock_async_websocket():
    """Create a mock async WebSocket connection."""
    ws = MagicMock()
    
    async def async_send(*args, **kwargs):
        return None
    
    async def async_receive(*args, **kwargs):
        return {"type": "message", "data": "test message"}
    
    async def async_close(*args, **kwargs):
        return None
    
    ws.send = MagicMock(side_effect=async_send)
    ws.receive = MagicMock(side_effect=async_receive)
    ws.close = MagicMock(side_effect=async_close)
    
    return ws


@pytest.fixture
def mock_file_system(temp_dir: Path):
    """Create a mock file system structure for testing."""
    structure = {
        "src": {
            "module1.py": "# Module 1 content",
            "module2.py": "# Module 2 content",
            "subdir": {
                "module3.py": "# Module 3 content",
            },
        },
        "tests": {
            "test_module1.py": "# Test module 1",
        },
        "config.json": '{"key": "value"}',
        "README.md": "# Test Project",
    }
    
    def create_structure(base_path: Path, structure: Dict):
        for name, content in structure.items():
            path = base_path / name
            if isinstance(content, dict):
                path.mkdir(exist_ok=True)
                create_structure(path, content)
            else:
                path.write_text(content)
    
    create_structure(temp_dir, structure)
    return temp_dir


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    yield


@pytest.fixture
def capture_logs(caplog):
    """Capture log messages for testing."""
    with caplog.at_level("DEBUG"):
        yield caplog


@pytest.fixture
def benchmark_timer():
    """Simple benchmark timer for performance testing."""
    import time
    
    class Timer:
        def __init__(self):
            self.times = []
        
        def __enter__(self):
            self.start = time.perf_counter()
            return self
        
        def __exit__(self, *args):
            self.end = time.perf_counter()
            self.times.append(self.end - self.start)
        
        @property
        def elapsed(self):
            return self.times[-1] if self.times else 0
        
        @property
        def total(self):
            return sum(self.times)
        
        @property
        def average(self):
            return sum(self.times) / len(self.times) if self.times else 0
    
    return Timer()


@pytest.fixture
def mock_external_api_responses():
    """Provide mock responses for external API calls."""
    return {
        "success": {"status": 200, "data": {"result": "success"}},
        "error": {"status": 500, "error": "Internal Server Error"},
        "not_found": {"status": 404, "error": "Not Found"},
        "unauthorized": {"status": 401, "error": "Unauthorized"},
        "rate_limited": {"status": 429, "error": "Too Many Requests"},
    }


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "asyncio: mark test as requiring asyncio"
    )