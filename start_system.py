"""
Quick Start Script for RAG Vidquest Enterprise System

This script helps you start the enterprise-grade RAG Vidquest system
with your migrated video data using Docker.
"""

import subprocess
import sys
import time
import requests
from pathlib import Path

def check_docker():
    """Check if Docker is running."""
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Docker found: {result.stdout.strip()}")
            return True
        else:
            print("❌ Docker not found. Please install Docker Desktop.")
            return False
    except FileNotFoundError:
        print("❌ Docker not found. Please install Docker Desktop.")
        return False

def check_docker_compose():
    """Check if Docker Compose is available."""
    try:
        result = subprocess.run(['docker', 'compose', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Docker Compose found: {result.stdout.strip()}")
            return True
        else:
            print("❌ Docker Compose not found.")
            return False
    except FileNotFoundError:
        print("❌ Docker Compose not found.")
        return False

def start_services():
    """Start the required services."""
    print("\n🚀 Starting RAG Vidquest services...")
    
    try:
        # Start core services
        subprocess.run(['docker compose', 'up', '-d', 'mongodb', 'qdrant', 'redis'], check=True)
        print("✅ Core services started (MongoDB, Qdrant, Redis)")
        
        # Wait a bit for services to initialize
        print("⏳ Waiting for services to initialize...")
        time.sleep(10)
        
        # Start Ollama
        subprocess.run(['docker compose', 'up', '-d', 'ollama'], check=True)
        print("✅ Ollama service started")
        
        # Wait for Ollama to be ready
        print("⏳ Waiting for Ollama to initialize...")
        time.sleep(15)
        
        # Pull the model
        print("📥 Pulling Gemma model...")
        subprocess.run(['docker', 'exec', 'ollama', 'ollama', 'pull', 'gemma:2b'], check=True)
        print("✅ Gemma model downloaded")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start services: {e}")
        return False

def start_application():
    """Start the RAG Vidquest application."""
    print("\n🎯 Starting RAG Vidquest application...")
    
    try:
        # Start the application
        subprocess.run(['docker compose', 'up', '-d', 'rag-vidquest'], check=True)
        print("✅ RAG Vidquest application started")
        
        # Wait for application to be ready
        print("⏳ Waiting for application to initialize...")
        time.sleep(10)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start application: {e}")
        return False

def check_health():
    """Check if the application is healthy."""
    print("\n🔍 Checking application health...")
    
    max_retries = 10
    for i in range(max_retries):
        try:
            response = requests.get('http://localhost:8000/health', timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ Application is healthy: {health_data['status']}")
                return True
            else:
                print(f"⏳ Application not ready yet (attempt {i+1}/{max_retries})")
        except requests.exceptions.RequestException:
            print(f"⏳ Application not ready yet (attempt {i+1}/{max_retries})")
        
        time.sleep(5)
    
    print("❌ Application health check failed")
    return False

def show_access_info():
    """Show access information."""
    print("\n" + "="*60)
    print("🎉 RAG VIDQUEST ENTERPRISE SYSTEM IS READY!")
    print("="*60)
    print("\n📊 Access Points:")
    print("• API Documentation: http://localhost:8000/docs")
    print("• Health Check: http://localhost:8000/health")
    print("• Metrics: http://localhost:8000/metrics")
    print("\n🔧 API Usage:")
    print("curl -X POST 'http://localhost:8000/query' \\")
    print("  -H 'Content-Type: application/json' \\")
    print("  -d '{\"query\": \"What is machine learning?\"}'")
    print("\n📁 Your Data:")
    print("• Videos: 8 video files with subtitles")
    print("• Frames: 6,638 extracted frames")
    print("• Clips: 3 pre-generated clips")
    print("• Total Size: ~2GB")
    print("\n🛠️ Management Commands:")
    print("• View logs: docker compose logs rag-vidquest")
    print("• Stop system: docker compose down")
    print("• Restart: docker compose restart rag-vidquest")
    print("• Deploy to production: docker compose -f docker compose.yml up -d")
    print("="*60)

def main():
    """Main function."""
    print("🎓 RAG Vidquest Enterprise System - Quick Start")
    print("="*50)
    
    # Check prerequisites
    if not check_docker():
        return False
    
    if not check_docker_compose():
        return False
    
    # Check if data exists
    data_dir = Path("./data")
    if not data_dir.exists():
        print("❌ Data directory not found. Please run migrate_data.py first.")
        return False
    
    print("✅ Data directory found")
    
    # Start services
    if not start_services():
        return False
    
    # Start application
    if not start_application():
        return False
    
    # Check health
    if not check_health():
        print("⚠️ Application may still be starting. Check logs with:")
        print("docker compose logs rag-vidquest")
        return False
    
    # Show access information
    show_access_info()
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n❌ Setup failed. Please check the errors above.")
        sys.exit(1)
    else:
        print("\n🎉 Setup completed successfully!")
