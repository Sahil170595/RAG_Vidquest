# RAG Vidquest - Enterprise Video RAG System

## Overview

RAG Vidquest is a production-ready Retrieval-Augmented Generation (RAG) system designed for querying video content using natural language. The system combines semantic search, AI-powered summarization, and video clip generation to provide intelligent responses based on video content.

## Architecture

The system follows a microservices architecture with the following components:

### Core Services

1. **FastAPI Application** (`src/api/`)
   - REST API endpoints
   - Request validation and authentication
   - Error handling and logging
   - Rate limiting and security

2. **RAG Service** (`src/services/rag.py`)
   - Semantic search orchestration
   - Content retrieval and processing
   - Response generation using LLM

3. **Model Services** (`src/models/services.py`)
   - Embedding generation using SentenceTransformers
   - LLM integration via Ollama
   - Model caching and optimization

4. **Video Services** (`src/services/video.py`)
   - Video file processing and validation
   - Frame extraction and clip generation
   - Subtitle processing

5. **Database Layer** (`src/database/connection.py`)
   - MongoDB for metadata storage
   - Qdrant for vector storage
   - Connection pooling and health checks

### Configuration Management

- **Settings** (`src/config/settings.py`): Centralized configuration with environment variable support
- **Logging** (`src/config/logging.py`): Structured logging with JSON format and rotation
- **Exceptions** (`src/core/exceptions.py`): Custom exception handling with error codes

## API Endpoints

### Query Videos
```http
POST /query
Content-Type: application/json

{
  "query": "What is machine learning?",
  "max_results": 5,
  "min_score": 0.3,
  "include_video_clip": true
}
```

### Health Check
```http
GET /health
```

### Metrics
```http
GET /metrics
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Environment (development/production) | `development` |
| `DEBUG` | Enable debug mode | `false` |
| `MONGODB_URL` | MongoDB connection string | `mongodb://localhost:27017/` |
| `QDRANT_HOST` | Qdrant host | `localhost` |
| `QDRANT_PORT` | Qdrant port | `6333` |
| `OLLAMA_URL` | Ollama API URL | `http://localhost:11434/api/chat` |
| `OLLAMA_MODEL` | Ollama model name | `gemma2:2b` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `SECRET_KEY` | Secret key for security | `your-secret-key` |

## Development

### Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start required services:
   ```bash
   docker-compose up -d mongodb qdrant ollama redis
   ```

3. Run the application:
   ```bash
   uvicorn src.api.app:app --reload
   ```

### Testing

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# All tests with coverage
pytest tests/ -v --cov=src --cov-report=html
```

### Code Quality

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

## Deployment

### Docker

```bash
# Development
docker-compose up -d

# Production
docker-compose --profile production up -d
```

### Kubernetes

```bash
kubectl apply -f k8s/
```

## Monitoring

### Health Checks

- Application health: `/health`
- Database connectivity
- Model service status

### Metrics

- Request metrics (response times, error rates)
- Resource metrics (CPU, memory)
- Business metrics (query volume, success rates)

### Logging

- Structured JSON logging
- Correlation IDs for request tracing
- Automatic log rotation

## Security

### Authentication

- API key authentication
- Rate limiting per client
- Input validation and sanitization

### Best Practices

- Non-root container execution
- Secrets management via environment variables
- Security scanning in CI/CD pipeline
- HTTPS enforcement

## Performance

### Caching

- Embedding cache for repeated queries
- Search result caching
- Redis for distributed caching

### Optimization

- Async/await for non-blocking I/O
- Connection pooling for databases
- Background task processing

### Scaling

- Horizontal scaling with multiple instances
- Load balancing with Nginx
- Database clustering support

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check MongoDB and Qdrant are running
   - Verify connection strings in environment variables

2. **Model Loading Issues**
   - Ensure Ollama is running and model is downloaded
   - Check model name in configuration

3. **Video Processing Errors**
   - Verify FFmpeg is installed
   - Check video file formats are supported

### Logs

```bash
# View application logs
docker-compose logs rag-vidquest

# View specific service logs
docker-compose logs mongodb
docker-compose logs qdrant
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

### Guidelines

- Follow PEP 8 style guidelines
- Write comprehensive tests
- Update documentation
- Use conventional commits

## License

MIT License - see LICENSE file for details.
