#!/bin/bash
# LinkedIn Knowledge Management System - Render Deployment Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
RENDER_CONFIG="render.yaml"
ENV_FILE=".env"

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

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites for Render deployment..."
    
    # Check if render.yaml exists
    if [ ! -f "$RENDER_CONFIG" ]; then
        error "render.yaml not found. Please ensure it exists in the project root."
        exit 1
    fi
    
    # Check if .env file exists
    if [ ! -f "$ENV_FILE" ]; then
        warning ".env file not found. Make sure to set environment variables in Render dashboard."
    fi
    
    # Check if git is available
    if ! command -v git &> /dev/null; then
        error "Git is not installed. Render requires Git for deployment."
        exit 1
    fi
    
    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        error "Not in a Git repository. Render requires Git for deployment."
        exit 1
    fi
    
    success "Prerequisites check passed"
}

# Validate configuration
validate_config() {
    log "Validating configuration for Render..."
    
    # Check if required files exist
    local required_files=("requirements.txt" "linkedin_scraper/api/app.py")
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            error "Required file not found: $file"
            exit 1
        fi
    done
    
    # Validate Python requirements
    if ! grep -q "fastapi" requirements.txt; then
        error "FastAPI not found in requirements.txt"
        exit 1
    fi
    
    if ! grep -q "uvicorn" requirements.txt; then
        error "Uvicorn not found in requirements.txt"
        exit 1
    fi
    
    success "Configuration validation passed"
}

# Prepare for deployment
prepare_deployment() {
    log "Preparing for Render deployment..."
    
    # Create necessary directories
    mkdir -p knowledge_repository
    mkdir -p cache
    mkdir -p logs
    
    # Ensure all changes are committed
    if ! git diff --quiet; then
        warning "You have uncommitted changes. Render deploys from Git."
        read -p "Do you want to commit changes now? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git add .
            git commit -m "Prepare for Render deployment"
            success "Changes committed"
        else
            warning "Proceeding with uncommitted changes. They won't be deployed."
        fi
    fi
    
    success "Deployment preparation completed"
}

# Generate deployment checklist
generate_checklist() {
    log "Generating Render deployment checklist..."
    
    cat << EOF

📋 RENDER DEPLOYMENT CHECKLIST
================================

Before deploying to Render, please ensure:

✅ Prerequisites:
   • Git repository is set up and changes are committed
   • render.yaml is configured correctly
   • requirements.txt includes all dependencies

✅ Environment Variables (Set in Render Dashboard):
   • GEMINI_API_KEY - Your Gemini API key
   • API_SECRET_KEY - Generated secure key
   • ENCRYPTION_KEY - Generated secure key (if encryption enabled)

✅ Optional Environment Variables:
   • SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD (for email alerts)
   • WEBHOOK_URL (for webhook notifications)

✅ Service Configuration:
   • Update CORS_ALLOW_ORIGINS with your Render domain
   • Adjust instance plan based on expected load
   • Configure Redis if using caching

✅ Post-Deployment:
   • Test health endpoint: https://your-app.onrender.com/api/v1/health
   • Test web interface: https://your-app.onrender.com/
   • Monitor logs for any issues

🔗 Render Dashboard: https://dashboard.render.com/

EOF
}

# Show deployment instructions
show_instructions() {
    log "Render Deployment Instructions:"
    
    cat << EOF

🚀 RENDER DEPLOYMENT STEPS
==========================

1. Push your code to GitHub/GitLab:
   git push origin main

2. Go to Render Dashboard:
   https://dashboard.render.com/

3. Create a new Web Service:
   • Connect your Git repository
   • Use the render.yaml configuration
   • Set environment variables in the dashboard

4. Deploy:
   • Render will automatically build and deploy
   • Monitor the build logs for any issues

5. Post-deployment:
   • Test the health endpoint
   • Configure custom domain (optional)
   • Set up monitoring and alerts

📚 Documentation: https://render.com/docs

EOF
}

# Run pre-deployment tests
run_tests() {
    log "Running pre-deployment tests..."
    
    # Test configuration
    if command -v python3 &> /dev/null; then
        if [ -f "quick_security_test.py" ]; then
            if python3 quick_security_test.py; then
                success "Security tests passed"
            else
                warning "Security tests failed. Please review before deploying."
            fi
        fi
        
        # Test imports
        if python3 -c "from linkedin_scraper.api.app import app; print('✅ App imports successfully')"; then
            success "Application imports successfully"
        else
            error "Application import failed. Please fix before deploying."
            exit 1
        fi
    else
        warning "Python3 not found. Skipping pre-deployment tests."
    fi
}

# Main deployment preparation function
main() {
    log "Starting Render deployment preparation..."
    
    check_prerequisites
    validate_config
    run_tests
    prepare_deployment
    generate_checklist
    show_instructions
    
    success "Render deployment preparation completed!"
    log "Your application is ready to deploy to Render."
    log "Follow the instructions above to complete the deployment."
}

# Help function
show_help() {
    echo "LinkedIn Knowledge Management System - Render Deployment Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --help      Show this help message"
    echo "  --check     Only run checks without preparation"
    echo ""
    echo "This script prepares your application for deployment to Render."
    echo "It validates configuration, runs tests, and provides deployment instructions."
}

# Parse command line arguments
case "$1" in
    --help)
        show_help
        exit 0
        ;;
    --check)
        check_prerequisites
        validate_config
        run_tests
        exit 0
        ;;
    *)
        main
        ;;
esac