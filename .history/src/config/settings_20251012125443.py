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
from pydantic import BaseModel, Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseSettings):
    """Database configuration settings."""
    
    mongodb_url: str = Field(default="mongodb://localhost:27017/")
    mongodb_database: str = Field(default="video_rag")
    qdrant_host: str = Field(default="localhost")
    qdrant_port: int = Field(default=6333)
    qdrant_collection: str = Field(default="video_embeddings")
    
    model_config = ConfigDict(env_prefix="DB_")


class ModelConfig(BaseSettings):
    """Model configuration settings."""
    
    embedding_model: str = Field(default="all-MiniLM-L6-v2")
    ollama_url: str = Field(default="http://localhost:11434/api/chat")
    ollama_model: str = Field(default="gemma3")
    max_tokens: int = Field(default=1000)
    temperature: float = Field(default=0.7)
    
    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v):
        if not 0.0 <= v <= 2.0:
            raise ValueError('Temperature must be between 0.0 and 2.0')
        return v


class PathConfig(BaseSettings):
    """Path configuration settings."""
    
    video_root: str = Field(default="./data/videos")
    clip_output: str = Field(default="./data/clips")
    frame_output: str = Field(default="./data/frames")
    subtitle_output: str = Field(default="./data/subtitles")
    
    def __post_init__(self):
        """Ensure output directories exist."""
        for path in [self.clip_output, self.frame_output, self.subtitle_output]:
            Path(path).mkdir(parents=True, exist_ok=True)


class SecurityConfig(BaseSettings):
    """Security configuration settings."""
    
    secret_key: str = Field(default="your-secret-key-change-in-production")
    api_key_header: str = Field(default="X-API-Key")
    allowed_origins: list = Field(default=["*"])
    rate_limit_per_minute: int = Field(default=60)
    
    @field_validator('secret_key')
    @classmethod
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError('Secret key must be at least 32 characters long')
        return v


class LoggingConfig(BaseSettings):
    """Logging configuration settings."""
    
    level: str = Field(default="INFO")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_path: Optional[str] = Field(default=None)
    max_file_size: int = Field(default=10485760)  # 10MB
    backup_count: int = Field(default=5)
    
    @field_validator('level')
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of {valid_levels}')
        return v.upper()


class MonitoringConfig(BaseSettings):
    """Monitoring and metrics configuration."""
    
    enable_metrics: bool = Field(default=True)
    metrics_port: int = Field(default=8000)
    health_check_interval: int = Field(default=30)
    enable_tracing: bool = Field(default=False)
    jaeger_endpoint: Optional[str] = Field(default=None)


class Config(BaseModel):
    """Main configuration class that aggregates all config sections."""
    
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    paths: PathConfig = Field(default_factory=PathConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    
    # Application settings
    app_name: str = "RAG Vidquest"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False)
    environment: str = Field(default="development")
    
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
            'database': self.database.model_dump(),
            'model': self.model.model_dump(),
            'paths': self.paths.model_dump(),
            'security': self.security.model_dump(),
            'logging': self.logging.model_dump(),
            'monitoring': self.monitoring.model_dump(),
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
