"""
Database connection and management utilities for RAG Vidquest.

Provides connection pooling, health checks, and proper error handling
for MongoDB and Qdrant vector database connections.
"""

from typing import Optional, Dict, Any, List
import asyncio
from contextlib import asynccontextmanager
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
import logging

from ..config.settings import config
from ..core.exceptions import DatabaseError, VectorDatabaseError, ErrorCode
from ..config.logging import LoggerMixin


class DatabaseManager(LoggerMixin):
    """Manages database connections with health checks and error handling."""
    
    def __init__(self):
        self._mongodb_client: Optional[MongoClient] = None
        self._qdrant_client: Optional[QdrantClient] = None
        self._is_connected = False
    
    async def connect(self) -> None:
        """Establish connections to all databases."""
        try:
            await self._connect_mongodb()
            await self._connect_qdrant()
            self._is_connected = True
            self.logger.info("Successfully connected to all databases")
        except Exception as e:
            self.logger.error(f"Failed to connect to databases: {e}")
            await self.disconnect()
            raise DatabaseError(
                f"Failed to establish database connections: {e}",
                ErrorCode.DATABASE_CONNECTION_ERROR,
                original_exception=e
            )
    
    async def _connect_mongodb(self) -> None:
        """Connect to MongoDB."""
        try:
            self._mongodb_client = MongoClient(
                config.database.mongodb_url,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=5000
            )
            
            # Test connection
            self._mongodb_client.admin.command('ping')
            self.logger.info(f"Connected to MongoDB at {config.database.mongodb_url}")
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            raise DatabaseError(
                f"Failed to connect to MongoDB: {e}",
                ErrorCode.DATABASE_CONNECTION_ERROR,
                original_exception=e
            )
    
    async def _connect_qdrant(self) -> None:
        """Connect to Qdrant vector database."""
        try:
            self._qdrant_client = QdrantClient(
                host=config.database.qdrant_host,
                port=config.database.qdrant_port,
                timeout=5
            )
            
            # Test connection
            collections = self._qdrant_client.get_collections()
            self.logger.info(f"Connected to Qdrant at {config.database.qdrant_host}:{config.database.qdrant_port}")
            
        except Exception as e:
            raise VectorDatabaseError(
                f"Failed to connect to Qdrant: {e}",
                ErrorCode.VECTOR_DB_CONNECTION_ERROR,
                original_exception=e
            )
    
    async def disconnect(self) -> None:
        """Close all database connections."""
        if self._mongodb_client:
            self._mongodb_client.close()
            self._mongodb_client = None
        
        if self._qdrant_client:
            # Qdrant client doesn't have explicit close method
            self._qdrant_client = None
        
        self._is_connected = False
        self.logger.info("Disconnected from all databases")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all databases."""
        health_status = {
            'mongodb': {'status': 'unknown', 'error': None},
            'qdrant': {'status': 'unknown', 'error': None},
            'overall': 'unknown'
        }
        
        # Check MongoDB
        try:
            if self._mongodb_client:
                self._mongodb_client.admin.command('ping')
                health_status['mongodb']['status'] = 'healthy'
            else:
                health_status['mongodb']['status'] = 'disconnected'
        except Exception as e:
            health_status['mongodb']['status'] = 'unhealthy'
            health_status['mongodb']['error'] = str(e)
        
        # Check Qdrant
        try:
            if self._qdrant_client:
                self._qdrant_client.get_collections()
                health_status['qdrant']['status'] = 'healthy'
            else:
                health_status['qdrant']['status'] = 'disconnected'
        except Exception as e:
            health_status['qdrant']['status'] = 'unhealthy'
            health_status['qdrant']['error'] = str(e)
        
        # Overall status
        if all(db['status'] == 'healthy' for db in [health_status['mongodb'], health_status['qdrant']]):
            health_status['overall'] = 'healthy'
        elif any(db['status'] == 'unhealthy' for db in [health_status['mongodb'], health_status['qdrant']]):
            health_status['overall'] = 'unhealthy'
        else:
            health_status['overall'] = 'degraded'
        
        return health_status
    
    @property
    def mongodb(self) -> MongoClient:
        """Get MongoDB client."""
        if not self._mongodb_client:
            raise DatabaseError("MongoDB client not initialized", ErrorCode.DATABASE_CONNECTION_ERROR)
        return self._mongodb_client
    
    @property
    def qdrant(self) -> QdrantClient:
        """Get Qdrant client."""
        if not self._qdrant_client:
            raise VectorDatabaseError("Qdrant client not initialized", ErrorCode.VECTOR_DB_CONNECTION_ERROR)
        return self._qdrant_client
    
    @property
    def is_connected(self) -> bool:
        """Check if all databases are connected."""
        return self._is_connected


class DatabaseRepository(LoggerMixin):
    """Base repository class for database operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    @property
    def mongodb(self) -> MongoClient:
        """Get MongoDB client."""
        return self.db_manager.mongodb
    
    @property
    def qdrant(self) -> QdrantClient:
        """Get Qdrant client."""
        return self.db_manager.qdrant


class VideoRepository(DatabaseRepository):
    """Repository for video-related database operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)
        self.collection = self.mongodb[config.database.mongodb_database]["videos"]
        self.questions_collection = self.mongodb[config.database.mongodb_database]["questions"]
    
    async def find_video_by_key(self, video_key: str) -> Optional[Dict[str, Any]]:
        """Find video document by key."""
        try:
            return self.collection.find_one({"video_key": video_key})
        except Exception as e:
            raise DatabaseError(
                f"Failed to find video {video_key}: {e}",
                ErrorCode.DATABASE_QUERY_ERROR,
                original_exception=e
            )
    
    async def find_questions_by_video_key(self, video_key: str) -> Optional[Dict[str, Any]]:
        """Find questions document by video key."""
        try:
            return self.questions_collection.find_one({"video_key": video_key})
        except Exception as e:
            raise DatabaseError(
                f"Failed to find questions for video {video_key}: {e}",
                ErrorCode.DATABASE_QUERY_ERROR,
                original_exception=e
            )
    
    async def insert_video(self, video_data: Dict[str, Any]) -> str:
        """Insert video document."""
        try:
            result = self.collection.insert_one(video_data)
            return str(result.inserted_id)
        except Exception as e:
            raise DatabaseError(
                f"Failed to insert video: {e}",
                ErrorCode.DATABASE_INSERT_ERROR,
                original_exception=e
            )
    
    async def update_video(self, video_key: str, update_data: Dict[str, Any]) -> bool:
        """Update video document."""
        try:
            result = self.collection.update_one(
                {"video_key": video_key},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            raise DatabaseError(
                f"Failed to update video {video_key}: {e}",
                ErrorCode.DATABASE_UPDATE_ERROR,
                original_exception=e
            )


class VectorRepository(DatabaseRepository):
    """Repository for vector database operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)
        self.collection_name = config.database.qdrant_collection
    
    async def search_similar(self, query_vector: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """Search for similar vectors."""
        try:
            results = self.qdrant.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit
            )
            
            return [
                {
                    'id': result.id,
                    'score': result.score,
                    'payload': result.payload
                }
                for result in results
            ]
        except Exception as e:
            raise VectorDatabaseError(
                f"Failed to search vectors: {e}",
                ErrorCode.VECTOR_DB_QUERY_ERROR,
                original_exception=e
            )
    
    async def insert_vectors(self, vectors: List[Dict[str, Any]]) -> bool:
        """Insert vectors into collection."""
        try:
            self.qdrant.upsert(
                collection_name=self.collection_name,
                points=vectors
            )
            return True
        except Exception as e:
            raise VectorDatabaseError(
                f"Failed to insert vectors: {e}",
                ErrorCode.VECTOR_DB_INSERT_ERROR,
                original_exception=e
            )
    
    async def create_collection(self, vector_size: int) -> bool:
        """Create vector collection."""
        try:
            self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config={"size": vector_size, "distance": "Cosine"}
            )
            return True
        except Exception as e:
            raise VectorDatabaseError(
                f"Failed to create collection: {e}",
                ErrorCode.VECTOR_DB_CONNECTION_ERROR,
                original_exception=e
            )


# Global database manager instance
db_manager = DatabaseManager()
