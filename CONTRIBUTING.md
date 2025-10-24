# Contributing to RAG Vidquest

Thank you for your interest in contributing to RAG Vidquest! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Process](#contributing-process)
- [Code Style](#code-style)
- [Testing](#testing)
- [Documentation](#documentation)
- [Issue Reporting](#issue-reporting)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

This project follows a code of conduct that we expect all contributors to adhere to. Please be respectful, inclusive, and constructive in all interactions.

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Create a new branch for your feature/fix
4. Make your changes
5. Test your changes
6. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Git

### Setup Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/Sahil170595/RAG_Vidquest.git
   cd RAG_Vidquest
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. Start the development environment:
   ```bash
   docker compose up -d
   ```

5. Run tests:
   ```bash
   pytest
   ```

## Contributing Process

### Types of Contributions

- **Bug fixes**: Fix existing issues
- **Features**: Add new functionality
- **Documentation**: Improve documentation
- **Tests**: Add or improve tests
- **Performance**: Optimize existing code
- **Refactoring**: Improve code structure

### Workflow

1. **Create an Issue**: If you're fixing a bug or adding a feature, create an issue first
2. **Fork and Branch**: Create a feature branch from `main`
3. **Develop**: Make your changes with proper tests
4. **Test**: Ensure all tests pass
5. **Document**: Update documentation if needed
6. **Submit PR**: Create a pull request with a clear description

## Code Style

### Python Style

We use the following tools for code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking

Run these before committing:

```bash
black src tests
isort src tests
flake8 src tests
mypy src
```

### Code Guidelines

- Follow PEP 8 style guidelines
- Use type hints for all functions
- Write docstrings for all public functions/classes
- Keep functions small and focused
- Use meaningful variable names
- Add comments for complex logic

### Example Code Style

```python
from typing import List, Optional
from pydantic import BaseModel

class QueryRequest(BaseModel):
    """Request model for video queries."""
    
    query: str
    max_results: int = 5
    
    def validate_query(self) -> bool:
        """Validate the query string."""
        return len(self.query.strip()) > 0
```

## Testing

### Test Structure

- **Unit Tests**: Test individual components (`tests/unit/`)
- **Integration Tests**: Test component interactions (`tests/integration/`)
- **End-to-End Tests**: Test complete workflows (`tests/e2e/`)

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_rag_service.py

# Run tests with specific markers
pytest -m "not slow"
```

### Writing Tests

- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)
- Mock external dependencies
- Test edge cases and error conditions
- Aim for high test coverage

### Example Test

```python
import pytest
from unittest.mock import Mock, patch
from src.services.rag import RAGService

@pytest.mark.asyncio
async def test_process_query_success():
    """Test successful query processing."""
    # Arrange
    mock_vector_repo = Mock()
    mock_video_repo = Mock()
    rag_service = RAGService(mock_vector_repo, mock_video_repo)
    
    # Act
    result = await rag_service.process_query("test query")
    
    # Assert
    assert result.query == "test query"
    assert result.summary is not None
```

## Documentation

### Documentation Types

- **API Documentation**: Auto-generated from docstrings
- **User Documentation**: README, Quick Start Guide
- **Developer Documentation**: Code comments, architecture docs
- **Deployment Documentation**: Docker, CI/CD setup

### Documentation Standards

- Use clear, concise language
- Include code examples
- Keep documentation up-to-date
- Use proper markdown formatting

## Issue Reporting

### Bug Reports

When reporting bugs, include:

- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Error messages/logs

### Feature Requests

For feature requests, include:

- Clear description of the feature
- Use case and motivation
- Proposed implementation (if applicable)
- Any relevant examples

## Pull Request Process

### PR Requirements

- [ ] All tests pass
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Clear commit messages
- [ ] Linked to relevant issues

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass
- [ ] New tests added
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

### Review Process

1. **Automated Checks**: CI/CD pipeline runs tests and linting
2. **Code Review**: Maintainers review the code
3. **Testing**: Manual testing if needed
4. **Approval**: At least one maintainer approval required
5. **Merge**: Squash and merge to main branch

## Getting Help

- **Discussions**: Use GitHub Discussions for questions
- **Issues**: Create issues for bugs and feature requests
- **Documentation**: Check existing documentation first

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project README

Thank you for contributing to RAG Vidquest! 🚀
