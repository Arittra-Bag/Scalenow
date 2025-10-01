#!/bin/bash
# LinkedIn Knowledge Management System - Development Docker Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.dev.yml"
ENV_FILE=".env.dev"

# Functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Create development environment file if it doesn't exist
create_dev_env() {
    if [ ! -f "$ENV_FILE" ]; then
        log "Creating development environment file..."
        
        cat > "$ENV_FILE" << EOF
# LinkedIn Knowledge Management System - Development Environment

# API Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Environment Settings
ENVIRONMENT=development
DEVELOPMENT_MODE=true
SERVER_DEBUG=true
SERVER_RELOAD=true
LOG_LEVEL=DEBUG
ENABLE_DEBUG_LOGGING=true

# Security (relaxed for development)
ENABLE_PII_DETECTION=true
SANITIZE_CONTENT=true
ENABLE_API_AUTHENTICATION=false

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
CORS_ALLOW_ORIGINS=*

# Storage
KNOWLEDGE_REPO_PATH=/app/knowledge_repository
CACHE_DB_PATH=/app/cache/knowledge_cache.db
LOG_FILE_PATH=/app/logs/linkedin_kms.log

# Rate Limiting (relaxed for development)
GEMINI_RATE_LIMIT_RPM=30
API_RATE_LIMIT_REQUESTS_PER_MINUTE=120

# Development Features
MOCK_API_RESPONSES=false
ENABLE_TEST_MODE=false
EOF
        
        success "Development environment file created at $ENV_FILE"
        warning "Please edit $ENV_FILE and add your Gemini API key"
    fi
}

# Start development environment
start_dev() {
    log "Starting development environment..."
    
    create_dev_env
    
    # Build and start services
    docker-compose -f "$COMPOSE_FILE" build
    docker-compose -f "$COMPOSE_FILE" up -d
    
    # Wait for services to be ready
    log "Waiting for services to be ready..."
    sleep 10
    
    # Show status
    docker-compose -f "$COMPOSE_FILE" ps
    
    success "Development environment started!"
    log "Services available at:"
    log "  • Web Interface: http://localhost:8000"
    log "  • API Documentation: http://localhost:8000/api/docs"
    log "  • Redis: localhost:6380"
    log "  • Adminer (if enabled): http://localhost:8080"
    log ""
    log "To view logs: docker-compose -f $COMPOSE_FILE logs -f"
    log "To stop: docker-compose -f $COMPOSE_FILE down"
}

# Stop development environment
stop_dev() {
    log "Stopping development environment..."
    docker-compose -f "$COMPOSE_FILE" down
    success "Development environment stopped"
}

# Show logs
show_logs() {
    docker-compose -f "$COMPOSE_FILE" logs -f
}

# Restart services
restart_dev() {
    log "Restarting development environment..."
    docker-compose -f "$COMPOSE_FILE" restart
    success "Development environment restarted"
}

# Clean up development environment
clean_dev() {
    log "Cleaning up development environment..."
    docker-compose -f "$COMPOSE_FILE" down -v --remove-orphans
    docker system prune -f
    success "Development environment cleaned up"
}

# Run tests in development environment
test_dev() {
    log "Running tests in development environment..."
    
    # Run the application container with test command
    docker-compose -f "$COMPOSE_FILE" exec linkedin-kms-dev python -m pytest tests/ -v
    
    success "Tests completed"
}

# Access development container shell
shell_dev() {
    log "Accessing development container shell..."
    docker-compose -f "$COMPOSE_FILE" exec linkedin-kms-dev /bin/bash
}

# Show help
show_help() {
    echo "LinkedIn Knowledge Management System - Development Docker Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start     Start development environment"
    echo "  stop      Stop development environment"
    echo "  restart   Restart development environment"
    echo "  logs      Show and follow logs"
    echo "  test      Run tests in development environment"
    echo "  shell     Access development container shell"
    echo "  clean     Clean up development environment (removes volumes)"
    echo "  help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start    Start development environment"
    echo "  $0 logs     Show application logs"
    echo "  $0 shell    Access container shell for debugging"
}

# Main function
main() {
    case "$1" in
        start)
            start_dev
            ;;
        stop)
            stop_dev
            ;;
        restart)
            restart_dev
            ;;
        logs)
            show_logs
            ;;
        test)
            test_dev
            ;;
        shell)
            shell_dev
            ;;
        clean)
            clean_dev
            ;;
        help|--help|-h)
            show_help
            ;;
        "")
            log "No command specified. Use 'help' to see available commands."
            show_help
            ;;
        *)
            error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"