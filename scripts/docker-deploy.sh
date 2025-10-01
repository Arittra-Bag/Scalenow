#!/bin/bash
# LinkedIn Knowledge Management System - Docker Deployment Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"
BACKUP_DIR="./backups"
LOG_FILE="./logs/deployment.log"

# Functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if .env file exists
    if [ ! -f "$ENV_FILE" ]; then
        error ".env file not found. Please create one from .env.template"
        exit 1
    fi
    
    success "Prerequisites check passed"
}

# Create necessary directories
create_directories() {
    log "Creating necessary directories..."
    
    mkdir -p logs
    mkdir -p backups
    mkdir -p nginx/ssl
    mkdir -p monitoring/prometheus
    mkdir -p monitoring/grafana/dashboards
    mkdir -p monitoring/grafana/datasources
    
    success "Directories created"
}

# Generate SSL certificates (self-signed for development)
generate_ssl_certs() {
    log "Checking SSL certificates..."
    
    if [ ! -f "nginx/ssl/cert.pem" ] || [ ! -f "nginx/ssl/key.pem" ]; then
        warning "SSL certificates not found. Generating self-signed certificates..."
        
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout nginx/ssl/key.pem \
            -out nginx/ssl/cert.pem \
            -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
        
        success "Self-signed SSL certificates generated"
    else
        success "SSL certificates found"
    fi
}

# Validate environment configuration
validate_config() {
    log "Validating configuration..."
    
    # Check if required environment variables are set
    if ! grep -q "GEMINI_API_KEY=" "$ENV_FILE"; then
        error "GEMINI_API_KEY not found in .env file"
        exit 1
    fi
    
    # Run configuration validation
    if command -v python3 &> /dev/null; then
        if python3 config_manager.py validate --env-file "$ENV_FILE"; then
            success "Configuration validation passed"
        else
            error "Configuration validation failed"
            exit 1
        fi
    else
        warning "Python3 not found. Skipping configuration validation."
    fi
}

# Build Docker images
build_images() {
    log "Building Docker images..."
    
    docker-compose -f "$COMPOSE_FILE" build --no-cache
    
    success "Docker images built successfully"
}

# Deploy services
deploy_services() {
    log "Deploying services..."
    
    # Stop existing services
    docker-compose -f "$COMPOSE_FILE" down
    
    # Start services
    docker-compose -f "$COMPOSE_FILE" up -d
    
    success "Services deployed successfully"
}

# Wait for services to be healthy
wait_for_health() {
    log "Waiting for services to be healthy..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker-compose -f "$COMPOSE_FILE" ps | grep -q "healthy"; then
            success "Services are healthy"
            return 0
        fi
        
        log "Attempt $attempt/$max_attempts - Waiting for services to be healthy..."
        sleep 10
        ((attempt++))
    done
    
    error "Services failed to become healthy within timeout"
    return 1
}

# Run post-deployment tests
run_tests() {
    log "Running post-deployment tests..."
    
    # Test API health endpoint
    if curl -f http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        success "API health check passed"
    else
        error "API health check failed"
        return 1
    fi
    
    # Test web interface
    if curl -f http://localhost:8000/ > /dev/null 2>&1; then
        success "Web interface check passed"
    else
        error "Web interface check failed"
        return 1
    fi
    
    success "Post-deployment tests passed"
}

# Show deployment status
show_status() {
    log "Deployment Status:"
    echo ""
    docker-compose -f "$COMPOSE_FILE" ps
    echo ""
    log "Services are available at:"
    log "  • Web Interface: http://localhost:8000"
    log "  • API Documentation: http://localhost:8000/api/docs"
    log "  • Health Check: http://localhost:8000/api/v1/health"
    
    if docker-compose -f "$COMPOSE_FILE" ps | grep -q "grafana"; then
        log "  • Grafana Dashboard: http://localhost:3000 (admin/admin123)"
    fi
    
    if docker-compose -f "$COMPOSE_FILE" ps | grep -q "prometheus"; then
        log "  • Prometheus: http://localhost:9090"
    fi
}

# Backup current deployment
backup_deployment() {
    if [ "$1" = "--backup" ]; then
        log "Creating backup of current deployment..."
        
        local backup_name="backup-$(date +%Y%m%d-%H%M%S)"
        local backup_path="$BACKUP_DIR/$backup_name"
        
        mkdir -p "$backup_path"
        
        # Backup volumes
        docker run --rm -v linkedin-kms_knowledge_data:/data -v "$backup_path":/backup alpine tar czf /backup/knowledge_data.tar.gz -C /data .
        docker run --rm -v linkedin-kms_cache_data:/data -v "$backup_path":/backup alpine tar czf /backup/cache_data.tar.gz -C /data .
        docker run --rm -v linkedin-kms_log_data:/data -v "$backup_path":/backup alpine tar czf /backup/log_data.tar.gz -C /data .
        
        success "Backup created at $backup_path"
    fi
}

# Main deployment function
main() {
    log "Starting LinkedIn Knowledge Management System deployment..."
    
    # Parse arguments
    backup_deployment "$@"
    
    # Run deployment steps
    check_prerequisites
    create_directories
    generate_ssl_certs
    validate_config
    build_images
    deploy_services
    
    # Wait for services and test
    if wait_for_health; then
        run_tests
        show_status
        success "Deployment completed successfully!"
    else
        error "Deployment failed - services are not healthy"
        log "Checking logs..."
        docker-compose -f "$COMPOSE_FILE" logs --tail=50
        exit 1
    fi
}

# Help function
show_help() {
    echo "LinkedIn Knowledge Management System - Docker Deployment Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --backup    Create backup before deployment"
    echo "  --help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                Deploy without backup"
    echo "  $0 --backup      Deploy with backup"
}

# Parse command line arguments
case "$1" in
    --help)
        show_help
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac