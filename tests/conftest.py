"""
Test configuration and utilities for RAG Vidquest.

Provides test fixtures, mocks, and utilities for comprehensive testing.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List
import tempfile
import os
from pathlib import Path

from src.config.settings import Config, DatabaseConfig, ModelConfig, PathConfig
from src.database.connection import DatabaseManager
from src.models.services import ModelManager
from src.services.rag import RAGService
from src.services.video import VideoService


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_config():
    """Create test configuration."""
    return Config(
        database=DatabaseConfig(
            mongodb_url="mongodb://localhost:27017/test_db",
            qdrant_host="localhost",
            qdrant_port=6333
        ),
        model=ModelConfig(
            embedding_model="all-MiniLM-L6-v2",
            ollama_url="http://localhost:11434/api/chat",
            ollama_model="test-model"
        ),
        paths=PathConfig(
            video_root="./test_data/videos",
            clip_output="./test_data/clips",
            frame_output="./test_data/frames",
            subtitle_output="./test_data/subtitles"
        )
    )


@pytest.fixture
def mock_db_manager():
    """Create mock database manager."""
    manager = Mock(spec=DatabaseManager)
    manager.connect = AsyncMock()
    manager.disconnect = AsyncMock()
    manager.health_check = AsyncMock(return_value={
        'mongodb': {'status': 'healthy'},
        'qdrant': {'status': 'healthy'},
        'overall': 'healthy'
    })
    manager.is_connected = True
    return manager


@pytest.fixture
def mock_model_manager():
    """Create mock model manager."""
    manager = Mock(spec=ModelManager)
    manager.initialize = AsyncMock()
    manager.health_check = AsyncMock(return_value={
        'embedding_service': {'status': 'healthy'},
        'llm_service': {'status': 'healthy'},
        'overall': 'healthy'
    })
    manager.is_initialized = True
    
    # Mock embedding service
    manager.embedding_service.encode_query = AsyncMock(return_value=[0.1] * 384)
    manager.embedding_service.encode_text = AsyncMock(return_value=Mock(
        embeddings=[[0.1] * 384],
        model_name="test-model",
        processing_time=0.1
    ))
    
    # Mock LLM service
    manager.llm_service.generate_response = AsyncMock(return_value=Mock(
        content="Test response",
        model_name="test-model",
        processing_time=0.5
    ))
    
    return manager


@pytest.fixture
def mock_video_service():
    """Create mock video service."""
    service = Mock(spec=VideoService)
    service.find_video_file = AsyncMock(return_value="/test/path/video.mp4")
    service.create_clip = AsyncMock(return_value="/test/path/clip.mp4")
    service.extract_frame = AsyncMock(return_value=Mock(
        frame_path="/test/path/frame.jpg",
        timestamp="00:01:30",
        timestamp_seconds=90.0,
        frame_number=1
    ))
    return service


@pytest.fixture
def mock_vector_repository():
    """Create mock vector repository."""
    repo = Mock()
    repo.search_similar = AsyncMock(return_value=[
        {
            'id': 1,
            'score': 0.95,
            'payload': {
                'text': 'Test content about machine learning',
                'video_key': 'test_video',
                'start': '00:01:00',
                'end': '00:02:00'
            }
        }
    ])
    repo.insert_vectors = AsyncMock(return_value=True)
    return repo


@pytest.fixture
def mock_video_repository():
    """Create mock video repository."""
    repo = Mock()
    repo.find_video_by_key = AsyncMock(return_value={
        'video_key': 'test_video',
        'title': 'Test Video',
        'duration': 300
    })
    repo.find_questions_by_video_key = AsyncMock(return_value={
        'video_key': 'test_video',
        'questions': []
    })
    return repo


@pytest.fixture
def sample_search_results():
    """Sample search results for testing."""
    return [
        Mock(
            text="This is about neural networks and deep learning",
            video_key="ml_video_1",
            start_time="00:05:30",
            end_time="00:07:15",
            score=0.92,
            metadata={'vector_id': 1}
        ),
        Mock(
            text="Convolutional neural networks are used for image processing",
            video_key="ml_video_2",
            start_time="00:12:00",
            end_time="00:14:30",
            score=0.88,
            metadata={'vector_id': 2}
        )
    ]


@pytest.fixture
def temp_directory():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_video_file(temp_directory):
    """Create sample video file for testing."""
    video_path = temp_directory / "test_video.mp4"
    # Create empty file (in real tests, you'd use actual video data)
    video_path.touch()
    return str(video_path)


@pytest.fixture
def sample_subtitle_file(temp_directory):
    """Create sample subtitle file for testing."""
    subtitle_path = temp_directory / "test_video.vtt"
    subtitle_content = """WEBVTT

00:00:01.000 --> 00:00:04.000
Welcome to this machine learning course

00:00:05.000 --> 00:00:08.000
Today we'll learn about neural networks
"""
    subtitle_path.write_text(subtitle_content)
    return str(subtitle_path)


class TestDataFactory:
    """Factory for creating test data."""
    
    @staticmethod
    def create_video_metadata():
        """Create sample video metadata."""
        return {
            'video_key': 'test_video_001',
            'title': 'Introduction to Machine Learning',
            'duration': 1800,  # 30 minutes
            'file_path': '/videos/test_video_001.mp4',
            'created_at': '2024-01-01T00:00:00Z'
        }
    
    @staticmethod
    def create_subtitle_segments():
        """Create sample subtitle segments."""
        return [
            {
                'start_time': '00:00:01.000',
                'end_time': '00:00:04.000',
                'text': 'Welcome to this machine learning course',
                'start_seconds': 1.0,
                'end_seconds': 4.0
            },
            {
                'start_time': '00:00:05.000',
                'end_time': '00:00:08.000',
                'text': 'Today we will learn about neural networks',
                'start_seconds': 5.0,
                'end_seconds': 8.0
            }
        ]
    
    @staticmethod
    def create_embedding_vector(dimensions=384):
        """Create sample embedding vector."""
        return [0.1] * dimensions
    
    @staticmethod
    def create_query_request():
        """Create sample query request."""
        return {
            'query': 'What is machine learning?',
            'max_results': 5,
            'min_score': 0.3,
            'include_video_clip': True
        }


@pytest.fixture
def test_data_factory():
    """Provide test data factory."""
    return TestDataFactory


# Async test utilities
def async_test(func):
    """Decorator for async test functions."""
    return pytest.mark.asyncio(func)


# Mock utilities
def mock_http_response(status_code=200, json_data=None, text_data=None):
    """Create mock HTTP response."""
    response = Mock()
    response.status_code = status_code
    response.json = Mock(return_value=json_data or {})
    response.text = text_data or ""
    response.raise_for_status = Mock()
    return response


def mock_ollama_response(content="Test response"):
    """Create mock Ollama response."""
    return {
        "model": "test-model",
        "message": {
            "role": "assistant",
            "content": content
        },
        "done": True
    }


# Test configuration overrides
@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment."""
    # Set test environment variables
    os.environ['ENVIRONMENT'] = 'test'
    os.environ['LOG_LEVEL'] = 'DEBUG'
    os.environ['DEBUG'] = 'true'
    
    yield
    
    # Cleanup after test
    for key in ['ENVIRONMENT', 'LOG_LEVEL', 'DEBUG']:
        os.environ.pop(key, None)
