# 🎓 RAG Vidquest - Enterprise Video RAG System

[![CI/CD Pipeline](https://github.com/Sahil170595/RAG_Vidquest/workflows/CI/CD%20Pipeline/badge.svg)](https://github.com/Sahil170595/RAG_Vidquest/actions)
[![Code Coverage](https://codecov.io/gh/Sahil170595/RAG_Vidquest/branch/main/graph/badge.svg)](https://codecov.io/gh/Sahil170595/RAG_Vidquest)
[![Security Scan](https://github.com/Sahil170595/RAG_Vidquest/workflows/Security%20Scan/badge.svg)](https://github.com/Sahil170595/RAG_Vidquest/security)
[![Docker](https://img.shields.io/docker/v/Sahil170595/rag-vidquest?label=docker)](https://hub.docker.com/r/Sahil170595/rag-vidquest)

A production-ready Retrieval-Augmented Generation (RAG) system for querying video content with enterprise-grade architecture, monitoring, security, and scalability.

## 🚀 Features

- **Semantic Video Search**: Find relevant video segments using natural language queries
- **AI-Powered Summarization**: Get intelligent summaries using Ollama/Gemma integration
- **Video Clip Generation**: Automatically extract relevant video clips
- **Enterprise Architecture**: Microservices, async processing, and horizontal scaling
- **Comprehensive Monitoring**: Health checks, metrics, and observability
- **Security First**: Authentication, rate limiting, and input validation
- **Production Ready**: Docker, CI/CD, and deployment configurations

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   MongoDB       │    │   Qdrant        │
│   (REST API)    │◄──►│   (Metadata)    │    │   (Vectors)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Ollama        │    │   Redis         │    │   Nginx         │
│   (LLM)         │    │   (Cache)       │    │   (Proxy)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📋 Prerequisites

- Python 3.11+
- Docker & Docker Compose
- MongoDB 7.0+
- Qdrant Vector Database
- Ollama with Gemma model
- FFmpeg for video processing

## 🛠️ Quick Start

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Sahil170595/RAG_Vidquest.git
   cd RAG_Vidquest
   ```

2. **Start services with Docker Compose**
   ```bash
   docker compose up -d
   ```

3. **Install Ollama model**
   ```bash
   docker exec ollama ollama pull gemma:2b
   ```

4. **Run the application**
   ```bash
   # Development mode
   docker compose up rag-vidquest
   
   # Or run locally
   pip install -r requirements.txt
   uvicorn src.api.app:app --reload
   ```

5. **Access the API**
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health
   - Metrics: http://localhost:8000/metrics

### Production Deployment

```bash
# Build production image
docker build --target production -t rag-vidquest:latest .

# Run with production profile
docker compose --profile production up -d
```

## 📚 API Documentation

### Core Endpoints

#### Query Videos
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

#### Health Check
```http
GET /health
```

#### Metrics
```http
GET /metrics
```

### Response Format

```json
{
  "query": "What is machine learning?",
  "summary": "Machine learning is a subset of artificial intelligence...",
  "search_results": [
    {
      "text": "Machine learning algorithms learn from data...",
      "video_key": "ml_intro_001",
      "start_time": "00:05:30",
      "end_time": "00:07:15",
      "score": 0.92,
      "metadata": {}
    }
  ],
  "video_clip_path": "/data/clips/ml_intro_001_clip.mp4",
  "processing_time": 1.5,
  "metadata": {
    "num_results": 3,
    "top_score": 0.92,
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Environment (development/production) | `development` |
| `DEBUG` | Enable debug mode | `false` |
| `MONGODB_URL` | MongoDB connection string | `mongodb://localhost:27017/` |
| `QDRANT_HOST` | Qdrant host | `localhost` |
| `QDRANT_PORT` | Qdrant port | `6333` |
| `OLLAMA_URL` | Ollama API URL | `http://localhost:11434/api/chat` |
| `OLLAMA_MODEL` | Ollama model name | `gemma:2b` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `SECRET_KEY` | Secret key for security | `your-secret-key` |

### Configuration Files

- `config.yaml` - Main configuration file
- `docker-compose.yml` - Service orchestration
- `Dockerfile` - Container configuration

## 🧪 Testing

### Run Tests

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# All tests with coverage
pytest tests/ -v --cov=src --cov-report=html

# Performance tests
locust -f tests/performance/locustfile.py --host=http://localhost:8000
```

### Test Coverage

```bash
# Generate coverage report
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

## 📊 Monitoring & Observability

### Health Checks

- **Application Health**: `/health` endpoint
- **Database Health**: MongoDB and Qdrant connectivity
- **Model Health**: Embedding and LLM service status

### Metrics

- **Request Metrics**: Response times, error rates
- **Resource Metrics**: CPU, memory, disk usage
- **Business Metrics**: Query volume, success rates

### Logging

- **Structured Logging**: JSON format with correlation IDs
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Log Rotation**: Automatic log file rotation

## 🔒 Security

### Authentication & Authorization

- **API Key Authentication**: Bearer token authentication
- **Rate Limiting**: Configurable per-minute limits
- **Input Validation**: Comprehensive request validation
- **CORS Protection**: Configurable cross-origin policies

### Security Best Practices

- **Non-root Containers**: All containers run as non-root users
- **Secrets Management**: Environment variable based secrets
- **Security Scanning**: Automated vulnerability scanning
- **HTTPS Enforcement**: SSL/TLS termination at proxy

## 🚀 Deployment

### Docker Deployment

```bash
# Development
docker compose up -d

# Production
docker compose --profile production up -d

# With monitoring
docker compose --profile production --profile monitoring up -d
```

### Kubernetes Deployment

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/

# Deploy with Helm
helm install rag-vidquest ./helm-chart
```

### Cloud Deployment

- **AWS**: ECS, EKS, or Lambda deployment
- **GCP**: Cloud Run or GKE deployment
- **Azure**: Container Instances or AKS deployment

## 📈 Performance Optimization

### Caching Strategy

- **Embedding Cache**: In-memory embedding cache
- **Search Cache**: Query result caching
- **Redis Cache**: Distributed caching layer

### Async Processing

- **Async/Await**: Non-blocking I/O operations
- **Connection Pooling**: Database connection optimization
- **Background Tasks**: Async task processing

### Scaling

- **Horizontal Scaling**: Multiple application instances
- **Load Balancing**: Nginx load balancer
- **Database Scaling**: MongoDB replica sets, Qdrant clustering

## 👥 Community & Learning

### Join Our Learning Community

This project is designed to be educational and welcoming to students and developers of all levels.

#### 🌟 Available Resources

- **GitHub Discussions**: [Ask questions](https://github.com/Sahil170595/RAG_Vidquest/discussions) and share ideas
- **GitHub Issues**: [Report bugs](https://github.com/Sahil170595/RAG_Vidquest/issues) and request features
- **Documentation**: Comprehensive guides in QUICK_START.md and CONTRIBUTING.md
- **Code Examples**: Real working codebase to study and learn from

#### 🎓 Educational Value

**For Students:**
- **Real-world Project**: Learn from a production-ready codebase
- **Modern Technologies**: FastAPI, Docker, MongoDB, Vector Databases
- **AI/ML Integration**: RAG systems, embeddings, and LLM integration
- **Best Practices**: Testing, documentation, and deployment

**For Developers:**
- **Enterprise Architecture**: Microservices, monitoring, and security
- **Open Source Contribution**: Practice contributing to real projects
- **Code Review Experience**: Learn through PR feedback and discussions
- **Portfolio Building**: Add meaningful contributions to your resume

#### 🏆 Recognition

- **Contributor Recognition**: Contributors listed in CONTRIBUTORS.md
- **GitHub Profile**: Showcase your contributions on your profile
- **Learning Portfolio**: Use this project in your academic/professional portfolio
- **Skill Development**: Gain experience with modern development tools

## 🎓 Student-Friendly Learning Environment

### For Undergraduate Students

This project provides a real-world example of enterprise software development with AI/ML integration. Perfect for learning modern development practices!

#### 🚀 Getting Started as a Student

1. **Prerequisites**
   - Basic Python knowledge (variables, functions, classes)
   - Understanding of APIs and HTTP requests
   - Familiarity with Git basics
   - Docker basics (we'll guide you!)

2. **Learning Path**
   ```
   Week 1-2: Setup & Understanding
   ├── Clone the repository
   ├── Run the application with Docker
   ├── Explore the codebase structure
   └── Read QUICK_START.md and CONTRIBUTING.md

   Week 3-4: First Contributions
   ├── Fix documentation typos
   ├── Add unit tests in tests/unit/
   ├── Improve error messages
   └── Add code comments

   Week 5-8: Feature Development
   ├── Implement new API endpoints
   ├── Add new video processing features
   ├── Improve error handling
   └── Optimize performance
   ```

#### 📚 Learning Resources

**Core Technologies Used:**
- [FastAPI Tutorial](https://fastapi.tiangolo.com/tutorial/) - Modern Python web framework
- [MongoDB University](https://university.mongodb.com/) - Database fundamentals
- [Qdrant Documentation](https://qdrant.tech/documentation/) - Vector databases
- [Docker for Beginners](https://docker-curriculum.com/) - Containerization

**AI/ML Concepts:**
- [RAG Systems Explained](https://docs.llamaindex.ai/en/stable/getting_started/concepts.html) - Retrieval Augmented Generation
- [Vector Embeddings Guide](https://platform.openai.com/docs/guides/embeddings) - Understanding embeddings
- [Ollama Documentation](https://ollama.ai/docs) - Local LLM deployment

**Development Practices:**
- [Git Workflow Guide](https://www.atlassian.com/git/tutorials/comparing-workflows)
- [Python Testing with pytest](https://docs.pytest.org/en/stable/getting-started.html)
- [API Design Best Practices](https://restfulapi.net/)

#### 🎯 Beginner-Friendly Tasks

**Good First Issues** (look for the `good first issue` label):
- 📝 Documentation improvements in README.md, QUICK_START.md
- 🧪 Adding unit tests in tests/unit/
- 🐛 Bug fixes in error handling
- 📊 Adding logging statements
- 🔧 Configuration improvements in src/config/
- 🧹 Code cleanup and refactoring

**Available Learning Opportunities:**
- Study the existing codebase structure
- Run and modify the test suite
- Experiment with API endpoints
- Learn Docker containerization

## 🤝 Contributing

### For Students

1. **Read the documentation**: Start with QUICK_START.md and CONTRIBUTING.md
2. **Fork the repository** and clone your fork
3. **Pick a good first issue** or ask for recommendations in GitHub Discussions
4. **Ask questions** - we're here to help through GitHub Issues and Discussions!

### Standard Contribution Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Write comprehensive tests
- Update documentation
- Use conventional commits
- Ask questions in PR comments - learning is encouraged!

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [Wiki](https://github.com/Sahil170595/RAG_Vidquest/wiki)
- **Issues**: [GitHub Issues](https://github.com/Sahil170595/RAG_Vidquest/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Sahil170595/RAG_Vidquest/discussions)

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Qdrant](https://qdrant.tech/) - Vector database
- [Ollama](https://ollama.ai/) - Local LLM runner
- [Sentence Transformers](https://www.sbert.net/) - Embedding models

---

**Made with ❤️ by the Enterprise Development Team**