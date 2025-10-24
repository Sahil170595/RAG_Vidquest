# 🚀 RAG Vidquest Enterprise System - Quick Start Guide

## 📋 Overview

RAG Vidquest is an enterprise-grade video question-answering system that allows you to query your video content using natural language. The system uses advanced AI techniques including semantic search, vector embeddings, and large language models to provide intelligent answers with relevant video clips.

## ⚡ Quick Start (5 Minutes)

### Prerequisites
- Docker Desktop installed and running
- Python 3.11+ (for local development)
- Git (for cloning the repository)

### 1. Clone and Setup
```bash
git clone https://github.com/Sahil170595/RAG_Vidquest.git
cd RAG_Vidquest
```

### 2. Start the System
```bash
# Start all services with Docker
python start_system.py

# Or manually with Docker Compose
docker compose up -d
```

### 3. Access the System
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics

### 4. Test Your First Query
```bash
curl -X POST 'http://localhost:8000/query' \
  -H 'Content-Type: application/json' \
  -d '{"query": "What is machine learning?"}'
```

## 🎯 What You Get

### 📊 Your Video Data
- **8 video files** with complete metadata
- **6,638 frame images** for visual search
- **8 subtitle files** for text-based queries
- **3 pre-generated clips** for quick access
- **Total size**: ~2GB of processed video content

### 🔧 Enterprise Features
- **REST API** with comprehensive documentation
- **Docker containerization** for easy deployment
- **Health monitoring** and metrics
- **Security features** with JWT authentication
- **Performance optimization** with Redis caching
- **Professional logging** and error handling
- **Scalable architecture** ready for production

## 🛠️ System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │────│   MongoDB       │    │   Qdrant        │
│   (Port 8000)   │    │   (Port 27017)  │    │   (Port 6333)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐    ┌─────────────────┐
                    │   Redis Cache    │    │   Ollama LLM    │
                    │   (Port 6379)    │    │   (Port 11434)  │
                    └─────────────────┘    └─────────────────┘
```

## 📚 API Usage Examples

### Basic Query
```python
import requests

response = requests.post('http://localhost:8000/query', json={
    "query": "What is machine learning?"
})

result = response.json()
print(f"Answer: {result['answer']}")
print(f"Sources: {result['sources']}")
print(f"Video Clip: {result['video_clip_path']}")
```

### Advanced Query with Parameters
```python
response = requests.post('http://localhost:8000/query', json={
    "query": "How do neural networks work?",
    "max_results": 5,
    "min_score": 0.7,
    "include_video_clip": True
})
```

### Health Check
```python
response = requests.get('http://localhost:8000/health')
print(f"Status: {response.json()['status']}")
```

## 🔧 Configuration

### Environment Variables
```bash
# Database
MONGODB_URL=mongodb://admin:password@mongodb:27017/video_rag
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# AI Models
OLLAMA_URL=http://ollama:11434/api/chat
OLLAMA_MODEL=gemma:2b
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Security
SECRET_KEY=your-super-secret-key-change-in-production
API_KEY_HEADER=X-API-Key

# Logging
LOG_LEVEL=INFO
ENVIRONMENT=production
```

### Custom Configuration
Edit `src/config/settings.py` to customize:
- Database connections
- Model parameters
- Security settings
- Logging configuration
- Path settings

## 📁 Data Management

### Adding New Videos
1. Place video files in `data/videos/`
2. Add corresponding subtitle files to `data/subtitles/`
3. Restart the system: `docker compose restart rag-vidquest`

### Data Structure
```
data/
├── videos/          # Original video files (.mp4, .vtt, .json)
├── subtitles/       # Extracted subtitle files (.txt)
├── frames/          # Extracted frame images (.jpg)
├── clips/          # Pre-generated video clips (.mp4)
├── metadata/        # Consolidated metadata and inventory
└── embeddings/     # Vector embeddings for search
```

## 🚀 Deployment Options

### Local Development
```bash
# Start with Docker Compose
docker compose up -d

# View logs
docker compose logs rag-vidquest

# Stop system
docker compose down
```

### Production Deployment
```bash
# Build and deploy
docker compose -f docker compose.yml up -d

# Scale services
docker compose up -d --scale rag-vidquest=3

# Monitor with logs
docker compose logs -f rag-vidquest
```

### Cloud Deployment
The system is ready for deployment on:
- **AWS**: Use ECS or EKS with RDS and ElastiCache
- **Google Cloud**: Use Cloud Run with Cloud SQL and Memorystore
- **Azure**: Use Container Instances with Azure Database and Redis Cache
- **Kubernetes**: Use the provided Docker images with Helm charts

## 🔍 Monitoring and Troubleshooting

### Health Checks
```bash
# Check system health
curl http://localhost:8000/health

# View metrics
curl http://localhost:8000/metrics

# Check service status
docker compose ps
```

### Common Issues

#### Service Not Starting
```bash
# Check logs
docker compose logs rag-vidquest

# Restart services
docker compose restart

# Rebuild if needed
docker compose up -d --build
```

#### Database Connection Issues
```bash
# Check MongoDB
docker compose logs mongodb

# Check Qdrant
docker compose logs qdrant

# Restart databases
docker compose restart mongodb qdrant
```

#### Performance Issues
```bash
# Check resource usage
docker stats

# Scale services
docker compose up -d --scale rag-vidquest=2

# Monitor metrics
curl http://localhost:8000/metrics
```

## 📈 Performance Optimization

### Caching
- Redis caching is enabled by default
- Query results are cached for 1 hour
- Vector embeddings are cached permanently

### Scaling
- Horizontal scaling: Add more app instances
- Vertical scaling: Increase container resources
- Database scaling: Use MongoDB replica sets

### Monitoring
- Prometheus metrics available at `/metrics`
- Structured logging with configurable levels
- Health checks for all services

## 🔒 Security Features

### Authentication
- JWT-based authentication
- API key support
- Rate limiting (60 requests/minute by default)

### Data Protection
- Input validation and sanitization
- SQL injection prevention
- XSS protection
- CORS configuration

### Network Security
- HTTPS support (configure SSL certificates)
- Internal service communication
- Firewall-ready architecture

## 🧪 Testing

### Run Tests
```bash
# Install dependencies
pip install -r requirements.txt

# Run unit tests
python -m pytest tests/unit/ -v

# Run integration tests
python -m pytest tests/integration/ -v

# Run all tests with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

### Test Coverage
- Unit tests for core services
- Integration tests for API endpoints
- Mock external dependencies
- Coverage reporting included

## 📖 Advanced Usage

### Custom Models
```python
# Use different embedding models
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-mpnet-base-v2')
# Update config to use new model
```

### Custom Prompts
```python
# Modify Ollama prompts in src/services/rag.py
CUSTOM_PROMPT = """
You are an expert video content analyzer. 
Answer the following question based on the provided context:
{context}

Question: {query}
"""
```

### Batch Processing
```python
# Process multiple queries
queries = ["What is AI?", "How do neural networks work?"]
results = []

for query in queries:
    response = requests.post('http://localhost:8000/query', json={"query": query})
    results.append(response.json())
```

## 🆘 Support and Resources

### Documentation
- **API Docs**: http://localhost:8000/docs
- **Code Documentation**: Inline docstrings
- **Architecture Guide**: See `docs/` directory

### Community
- **GitHub Issues**: Report bugs and feature requests
- **Discussions**: Ask questions and share ideas
- **Contributing**: See CONTRIBUTING.md

### Professional Support
For enterprise support, custom development, or consulting:
- Contact: 147995121+Sahil170595@users.noreply.github.com
- Documentation: https://github.com/Sahil170595/RAG_Vidquest/wiki
- Training: Available upon request

## 🎉 Success!

You now have a fully functional, enterprise-grade RAG Vidquest system! The system is:

- ✅ **Production-ready** with Docker deployment
- ✅ **Scalable** with modular architecture
- ✅ **Secure** with authentication and validation
- ✅ **Monitored** with health checks and metrics
- ✅ **Documented** with comprehensive API docs
- ✅ **Tested** with unit and integration tests

**Happy querying!** 🎓✨

---

*For more detailed information, see the full documentation in the `docs/` directory or visit the API documentation at http://localhost:8000/docs*
