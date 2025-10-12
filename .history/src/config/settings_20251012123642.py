"""
Configuration management for RAG Vidquest.

Handles environment variables, validation, and configuration loading
with proper error handling and type safety.
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseSettings):
    """Database configuration settings."""
    
    mongodb_url: str = Field(default="mongodb://localhost:27017/", env="MONGODB_URL")
    mongodb_database: str = Field(default="video_rag", env="MONGODB_DATABASE")
    qdrant_host: str = Field(default="localhost", env="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, env="QDRANT_PORT")
    qdrant_collection: str = Field(default="video_embeddings", env="QDRANT_COLLECTION")
    
    class Config:
        env_prefix = "DB_"


class ModelConfig(BaseSettings):
    """Model configuration settings."""
    
    embedding_model: str = Field(default="all-MiniLM-L6-v2", env="EMBEDDING_MODEL")
    ollama_url: str = Field(default="http://localhost:11434/api/chat", env="OLLAMA_URL")
    ollama_model: str = Field(default="gemma3", env="OLLAMA_MODEL")
    max_tokens: int = Field(default=1000, env="MAX_TOKENS")
    temperature: float = Field(default=0.7, env="TEMPERATURE")
    
    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v):
        if not 0.0 <= v <= 2.0:
            raise ValueError('Temperature must be between 0.0 and 2.0')
        return v


class PathConfig(BaseSettings):
    """Path configuration settings."""
    
    video_root: str = Field(default="./data/videos", env="VIDEO_ROOT")
    clip_output: str = Field(default="./data/clips", env="CLIP_OUTPUT")
    frame_output: str = Field(default="./data/frames", env="FRAME_OUTPUT")
    subtitle_output: str = Field(default="./data/subtitles", env="SUBTITLE_OUTPUT")
    
    def __post_init__(self):
        """Ensure output directories exist."""
        for path in [self.clip_output, self.frame_output, self.subtitle_output]:
            Path(path).mkdir(parents=True, exist_ok=True)


class SecurityConfig(BaseSettings):
    """Security configuration settings."""
    
    secret_key: str = Field(default="your-secret-key-change-in-production", env="SECRET_KEY")
    api_key_header: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    allowed_origins: list = Field(default=["*"], env="ALLOWED_ORIGINS")
    rate_limit_per_minute: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    
    @field_validator('secret_key')
    @classmethod
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError('Secret key must be at least 32 characters long')
        return v


class LoggingConfig(BaseSettings):
    """Logging configuration settings."""
    
    level: str = Field(default="INFO", env="LOG_LEVEL")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", env="LOG_FORMAT")
    file_path: Optional[str] = Field(default=None, env="LOG_FILE_PATH")
    max_file_size: int = Field(default=10485760, env="LOG_MAX_FILE_SIZE")  # 10MB
    backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")
    
    @field_validator('level')
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of {valid_levels}')
        return v.upper()


class MonitoringConfig(BaseSettings):
    """Monitoring and metrics configuration."""
    
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=8000, env="METRICS_PORT")
    health_check_interval: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    enable_tracing: bool = Field(default=False, env="ENABLE_TRACING")
    jaeger_endpoint: Optional[str] = Field(default=None, env="JAEGER_ENDPOINT")


@dataclass
class Config:
    """Main configuration class that aggregates all config sections."""
    
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    paths: PathConfig = field(default_factory=PathConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    # Application settings
    app_name: str = "RAG Vidquest"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    @classmethod
    def from_file(cls, config_path: str) -> 'Config':
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Create config sections
            database = DatabaseConfig(**config_data.get('database', {}))
            model = ModelConfig(**config_data.get('model', {}))
            paths = PathConfig(**config_data.get('paths', {}))
            security = SecurityConfig(**config_data.get('security', {}))
            logging = LoggingConfig(**config_data.get('logging', {}))
            monitoring = MonitoringConfig(**config_data.get('monitoring', {}))
            
            return cls(
                database=database,
                model=model,
                paths=paths,
                security=security,
                logging=logging,
                monitoring=monitoring,
                **config_data.get('app', {})
            )
        except Exception as e:
            logging.error(f"Failed to load config from file {config_path}: {e}")
            raise
    
    def validate(self) -> bool:
        """Validate configuration settings."""
        try:
            # Validate database connectivity
            if not self.database.mongodb_url:
                raise ValueError("MongoDB URL is required")
            
            # Validate paths exist or can be created
            for path_name, path_value in [
                ("video_root", self.paths.video_root),
                ("clip_output", self.paths.clip_output),
                ("frame_output", self.paths.frame_output),
                ("subtitle_output", self.paths.subtitle_output)
            ]:
                try:
                    Path(path_value).mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    raise ValueError(f"Cannot create or access {path_name}: {path_value} - {e}")
            
            return True
        except Exception as e:
            logging.error(f"Configuration validation failed: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'database': self.database.dict(),
            'model': self.model.dict(),
            'paths': self.paths.dict(),
            'security': self.security.dict(),
            'logging': self.logging.dict(),
            'monitoring': self.monitoring.dict(),
            'app_name': self.app_name,
            'app_version': self.app_version,
            'debug': self.debug,
            'environment': self.environment
        }


# Global configuration instance
config = Config()

# Validate configuration on import
if not config.validate():
    raise RuntimeError("Invalid configuration detected. Please check your environment variables and settings.")
