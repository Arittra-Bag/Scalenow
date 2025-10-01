# Deployment Guide

This guide covers deploying the LinkedIn Knowledge Scraper in various environments.

## Prerequisites

- Python 3.9 or higher
- Google Gemini API key
- Git (for repository management)
- Sufficient disk space for knowledge repository and cache

## Environment Setup

### 1. Configuration

Create a `.env` file with your configuration:

```env
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Paths (adjust for your deployment)
KNOWLEDGE_REPO_PATH=/app/data/knowledge_repository
CACHE_DB_PATH=/app/data/cache/knowledge_cache.db
LOG_FILE_PATH=/app/logs/scraper.log

# Environment
ENVIRONMENT=production
ENABLE_PII_DETECTION=true
SANITIZE_CONTENT=true
LOG_LEVEL=INFO

# Rate Limiting
GEMINI_RATE_LIMIT_RPM=60
GEMINI_RATE_LIMIT_RPD=1000

# Web Interface
WEB_SERVER_HOST=0.0.0.0
WEB_SERVER_PORT=8000
WEB_SERVER_DEBUG=false

# Security
API_SECRET_KEY=your_secure_secret_key_here
CORS_ALLOW_ORIGINS=https://yourdomain.com

# Monitoring
ENABLE_METRICS=true
METRICS_EXPORT_INTERVAL=300
ALERT_WEBHOOK_URL=https://hooks.slack.com/your/webhook/url
```

### 2. Dependencies

Install production dependencies:

```bash
pip install -r requirements.txt
```

For development:
```bash
pip install -r requirements-dev.txt
```

## Local Development

### Quick Start

1. Clone and setup:
```bash
git clone <repository-url>
cd linkedin-knowledge-scraper
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

3. Initialize and test:
```bash
python -m linkedin_scraper.main --help
python -m linkedin_scraper.main --url "https://linkedin.com/posts/sample/post"
```

4. Start web interface:
```bash
python -m linkedin_scraper.web.app
```

### Development Tools

Run tests:
```bash
pytest tests/ -v
```

Code formatting:
```bash
black linkedin_scraper/
isort linkedin_scraper/
```

Type checking:
```bash
mypy linkedin_scraper/
```

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data/knowledge_repository \
    /app/data/cache \
    /app/logs

# Set environment variables
ENV PYTHONPATH=/app
ENV KNOWLEDGE_REPO_PATH=/app/data/knowledge_repository
ENV CACHE_DB_PATH=/app/data/cache/knowledge_cache.db
ENV LOG_FILE_PATH=/app/logs/scraper.log

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["python", "-m", "linkedin_scraper.web.app"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  linkedin-scraper:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - ENVIRONMENT=production
      - WEB_SERVER_HOST=0.0.0.0
      - WEB_SERVER_PORT=8000
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Optional: Add a reverse proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - linkedin-scraper
    restart: unless-stopped
```

### Build and Run

```bash
# Build image
docker build -t linkedin-scraper .

# Run container
docker run -d \
  --name linkedin-scraper \
  -p 8000:8000 \
  -e GEMINI_API_KEY=your_api_key \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  linkedin-scraper

# Using docker-compose
docker-compose up -d
```

## Cloud Deployment

### Render

1. **Connect Repository**
   - Connect your GitHub repository to Render
   - Select "Web Service" deployment type

2. **Configure Build**
   ```yaml
   # render.yaml
   services:
     - type: web
       name: linkedin-scraper
       env: python
       buildCommand: pip install -r requirements.txt
       startCommand: python -m linkedin_scraper.web.app
       envVars:
         - key: GEMINI_API_KEY
           sync: false
         - key: ENVIRONMENT
           value: production
         - key: WEB_SERVER_HOST
           value: 0.0.0.0
         - key: WEB_SERVER_PORT
           value: 10000
   ```

3. **Set Environment Variables**
   - Add all required environment variables in Render dashboard
   - Ensure `WEB_SERVER_PORT` matches Render's assigned port

4. **Deploy**
   - Push changes to trigger deployment
   - Monitor deployment logs

### Google Cloud Platform

#### Cloud Run

1. **Prepare for deployment**:
```bash
# Create cloudbuild.yaml
cat > cloudbuild.yaml << EOF
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/\$PROJECT_ID/linkedin-scraper', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/\$PROJECT_ID/linkedin-scraper']
EOF
```

2. **Build and deploy**:
```bash
# Set project ID
export PROJECT_ID=your-gcp-project-id

# Build image
gcloud builds submit --tag gcr.io/$PROJECT_ID/linkedin-scraper

# Deploy to Cloud Run
gcloud run deploy linkedin-scraper \
  --image gcr.io/$PROJECT_ID/linkedin-scraper \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your_api_key,ENVIRONMENT=production \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 10
```

#### App Engine

1. **Create app.yaml**:
```yaml
runtime: python39

env_variables:
  GEMINI_API_KEY: your_api_key
  ENVIRONMENT: production
  WEB_SERVER_HOST: 0.0.0.0
  WEB_SERVER_PORT: 8080

automatic_scaling:
  min_instances: 1
  max_instances: 10
  target_cpu_utilization: 0.6

resources:
  cpu: 1
  memory_gb: 1
  disk_size_gb: 10
```

2. **Deploy**:
```bash
gcloud app deploy
```

### AWS

#### Elastic Beanstalk

1. **Create Dockerrun.aws.json**:
```json
{
  "AWSEBDockerrunVersion": "1",
  "Image": {
    "Name": "your-docker-image",
    "Update": "true"
  },
  "Ports": [
    {
      "ContainerPort": "8000"
    }
  ]
}
```

2. **Deploy**:
```bash
# Install EB CLI
pip install awsebcli

# Initialize and deploy
eb init
eb create production
eb deploy
```

#### ECS with Fargate

1. **Create task definition**:
```json
{
  "family": "linkedin-scraper",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "linkedin-scraper",
      "image": "your-ecr-repo/linkedin-scraper:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "GEMINI_API_KEY",
          "value": "your_api_key"
        },
        {
          "name": "ENVIRONMENT",
          "value": "production"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/linkedin-scraper",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

## Production Considerations

### Security

1. **Environment Variables**
   - Never commit API keys to version control
   - Use secure secret management (AWS Secrets Manager, GCP Secret Manager)
   - Rotate API keys regularly

2. **Network Security**
   - Use HTTPS in production
   - Configure proper CORS settings
   - Implement rate limiting
   - Use a reverse proxy (nginx, CloudFlare)

3. **Access Control**
   - Implement authentication for admin endpoints
   - Use API keys for programmatic access
   - Monitor access logs

### Performance

1. **Resource Allocation**
   - Monitor CPU and memory usage
   - Scale based on processing load
   - Use appropriate instance sizes

2. **Caching**
   - Configure cache size limits
   - Implement cache cleanup policies
   - Monitor cache hit rates

3. **Database Optimization**
   - Regular database maintenance
   - Index optimization for search queries
   - Backup strategies

### Monitoring

1. **Health Checks**
   - Configure health check endpoints
   - Monitor component health
   - Set up automated alerts

2. **Logging**
   - Centralized log aggregation
   - Log rotation policies
   - Error tracking and alerting

3. **Metrics**
   - Processing success/failure rates
   - API response times
   - Resource utilization
   - Business metrics (knowledge items processed)

### Backup and Recovery

1. **Data Backup**
   - Regular knowledge repository backups
   - Database backups
   - Configuration backups

2. **Disaster Recovery**
   - Multi-region deployment
   - Automated failover
   - Recovery procedures documentation

## Scaling

### Horizontal Scaling

1. **Load Balancing**
   - Use load balancer for multiple instances
   - Session affinity considerations
   - Health check configuration

2. **Database Scaling**
   - Read replicas for search queries
   - Database sharding strategies
   - Connection pooling

### Vertical Scaling

1. **Resource Optimization**
   - Profile memory usage
   - CPU optimization
   - I/O optimization

2. **Caching Strategies**
   - Redis for distributed caching
   - CDN for static assets
   - Application-level caching

## Maintenance

### Regular Tasks

1. **Updates**
   - Security patches
   - Dependency updates
   - Feature updates

2. **Cleanup**
   - Log rotation
   - Cache cleanup
   - Old data archival

3. **Monitoring**
   - Performance reviews
   - Error analysis
   - Capacity planning

### Troubleshooting

1. **Common Issues**
   - API rate limits
   - Memory leaks
   - Database locks
   - Network timeouts

2. **Debug Tools**
   - Application logs
   - System metrics
   - Database queries
   - Network traces

## Environment-Specific Configurations

### Development
```env
ENVIRONMENT=development
LOG_LEVEL=DEBUG
WEB_SERVER_DEBUG=true
ENABLE_METRICS=false
```

### Staging
```env
ENVIRONMENT=staging
LOG_LEVEL=INFO
WEB_SERVER_DEBUG=false
ENABLE_METRICS=true
```

### Production
```env
ENVIRONMENT=production
LOG_LEVEL=WARNING
WEB_SERVER_DEBUG=false
ENABLE_METRICS=true
ALERT_WEBHOOK_URL=your_alert_webhook
```

## SSL/TLS Configuration

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://linkedin-scraper:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

This deployment guide provides comprehensive instructions for deploying the LinkedIn Knowledge Scraper in various environments, from local development to production cloud deployments.