"""
Simple Test Script for RAG Vidquest

This script tests the core functionality without complex mocking.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from src.config.settings import Config
        print("OK Config imported successfully")
        
        from src.core.exceptions import RAGVidquestException
        print("OK Exceptions imported successfully")
        
        from src.models.services import QueryRequest, QueryResponse
        print("OK Models imported successfully")
        
        from src.services.video import VideoService
        print("OK Video service imported successfully")
        
        from src.services.rag import RAGService
        print("OK RAG service imported successfully")
        
        from src.api.app import app
        print("OK FastAPI app imported successfully")
        
        return True
        
    except Exception as e:
        print(f"ERROR Import failed: {e}")
        return False

def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")
    
    try:
        from src.config.settings import Config
        
        config = Config()
        print(f"OK Config loaded: {config.app_name} v{config.app_version}")
        print(f"OK Environment: {config.environment}")
        print(f"OK Debug mode: {config.debug}")
        
        return True
        
    except Exception as e:
        print(f"ERROR Config test failed: {e}")
        return False

def test_models():
    """Test Pydantic models."""
    print("\nTesting models...")
    
    try:
        from src.models.services import QueryRequest, QueryResponse
        
        # Test QueryRequest
        request = QueryRequest(query="What is machine learning?")
        print(f"OK QueryRequest created: {request.query}")
        
        # Test QueryResponse
        response = QueryResponse(
            query="What is machine learning?",
            answer="Machine learning is...",
            sources=["source1", "source2"],
            video_clip_path="/path/to/clip.mp4"
        )
        print(f"OK QueryResponse created: {response.query}")
        
        return True
        
    except Exception as e:
        print(f"ERROR Models test failed: {e}")
        return False

def test_video_service():
    """Test video service."""
    print("\nTesting video service...")
    
    try:
        from src.services.video import VideoService
        from src.config.settings import Config
        
        config = Config()
        video_service = VideoService(config)
        
        # Test finding video path (should return None for non-existent video)
        result = video_service.find_video_path("nonexistent_video")
        print(f"OK Video service created, find_video_path returned: {result}")
        
        return True
        
    except Exception as e:
        print(f"ERROR Video service test failed: {e}")
        return False

def test_data_structure():
    """Test that data structure exists."""
    print("\nTesting data structure...")
    
    data_dir = Path("./data")
    if not data_dir.exists():
        print("ERROR Data directory not found")
        return False
    
    print("OK Data directory exists")
    
    # Check subdirectories
    subdirs = ["videos", "subtitles", "frames", "clips", "metadata"]
    for subdir in subdirs:
        subdir_path = data_dir / subdir
        if subdir_path.exists():
            file_count = len(list(subdir_path.rglob("*")))
            print(f"OK {subdir}/ directory exists with {file_count} files")
        else:
            print(f"ERROR {subdir}/ directory not found")
            return False
    
    return True

def test_fastapi_app():
    """Test FastAPI app creation."""
    print("\nTesting FastAPI app...")
    
    try:
        from src.api.app import app
        
        print(f"OK FastAPI app created: {app.title}")
        print(f"OK App version: {app.version}")
        
        # Check routes
        routes = [route.path for route in app.routes]
        print(f"OK Routes available: {len(routes)} routes")
        
        return True
        
    except Exception as e:
        print(f"ERROR FastAPI app test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("RAG Vidquest - Simple Test Suite")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_config,
        test_models,
        test_video_service,
        test_data_structure,
        test_fastapi_app
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"ERROR Test {test.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("All tests passed! The system is ready.")
        return True
    else:
        print("Some tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
