#!/bin/bash
# LinkedIn Knowledge Management System - Google Cloud Platform Deployment Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=""
REGION="us-central1"
SERVICE_NAME="linkedin-kms"
APP_YAML="gcp/app.yaml"
CLOUDBUILD_YAML="gcp/cloudbuild.yaml"

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
    log "Checking prerequisites for GCP deployment..."
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        error "Google Cloud SDK is not installed. Please install it first:"
        error "https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
    
    # Check if user is authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n 1 > /dev/null; then
        error "Not authenticated with Google Cloud. Please run: gcloud auth login"
        exit 1
    fi
    
    # Check if project is set
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
    if [ -z "$PROJECT_ID" ]; then
        error "No GCP project set. Please run: gcloud config set project YOUR_PROJECT_ID"
        exit 1
    fi
    
    log "Using GCP project: $PROJECT_ID"
    
    # Check if required files exist
    if [ ! -f "$APP_YAML" ]; then
        error "app.yaml not found at $APP_YAML"
        exit 1
    fi
    
    success "Prerequisites check passed"
}

# Enable required APIs
enable_apis() {
    log "Enabling required GCP APIs..."
    
    local apis=(
        "appengine.googleapis.com"
        "cloudbuild.googleapis.com"
        "cloudlogging.googleapis.com"
        "cloudmonitoring.googleapis.com"
        "storage.googleapis.com"
        "secretmanager.googleapis.com"
    )
    
    for api in "${apis[@]}"; do
        log "Enabling $api..."
        gcloud services enable "$api" --project="$PROJECT_ID"
    done
    
    success "Required APIs enabled"
}

# Create App Engine application if it doesn't exist
create_app_engine() {
    log "Checking App Engine application..."
    
    if ! gcloud app describe --project="$PROJECT_ID" > /dev/null 2>&1; then
        log "Creating App Engine application..."
        gcloud app create --region="$REGION" --project="$PROJECT_ID"
        success "App Engine application created"
    else
        success "App Engine application already exists"
    fi
}

# Create Cloud Storage bucket for build artifacts
create_storage_bucket() {
    log "Creating Cloud Storage bucket for build artifacts..."
    
    local bucket_name="${PROJECT_ID}-build-artifacts"
    
    if ! gsutil ls -b "gs://$bucket_name" > /dev/null 2>&1; then
        gsutil mb -p "$PROJECT_ID" -l "$REGION" "gs://$bucket_name"
        success "Storage bucket created: gs://$bucket_name"
    else
        success "Storage bucket already exists: gs://$bucket_name"
    fi
}

# Set up secrets in Secret Manager
setup_secrets() {
    log "Setting up secrets in Secret Manager..."
    
    # Check if .env file exists for reference
    if [ -f ".env" ]; then
        warning "Found .env file. Please manually create these secrets in Secret Manager:"
        
        # Extract secret keys from .env
        grep -E "^(GEMINI_API_KEY|API_SECRET_KEY|ENCRYPTION_KEY)" .env | while read -r line; do
            key=$(echo "$line" | cut -d'=' -f1)
            echo "  • $key"
        done
        
        echo ""
        echo "Create secrets with:"
        echo "  gcloud secrets create GEMINI_API_KEY --data-file=- <<< 'your_api_key'"
        echo "  gcloud secrets create API_SECRET_KEY --data-file=- <<< 'your_secret_key'"
        echo ""
    else
        warning "No .env file found. Please create secrets manually in Secret Manager."
    fi
    
    # Grant App Engine access to secrets
    local app_engine_sa="${PROJECT_ID}@appspot.gserviceaccount.com"
    
    log "Granting App Engine service account access to secrets..."
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$app_engine_sa" \
        --role="roles/secretmanager.secretAccessor" || true
    
    success "Secret Manager setup completed"
}

# Update app.yaml with project-specific values
update_app_yaml() {
    log "Updating app.yaml with project-specific values..."
    
    # Create a temporary app.yaml with project ID
    cp "$APP_YAML" "${APP_YAML}.tmp"
    
    # Replace placeholder values
    sed -i.bak "s/your-project-id/$PROJECT_ID/g" "${APP_YAML}.tmp"
    sed -i.bak "s/your-project.appspot.com/${PROJECT_ID}.appspot.com/g" "${APP_YAML}.tmp"
    
    success "app.yaml updated with project values"
}

# Run pre-deployment tests
run_tests() {
    log "Running pre-deployment tests..."
    
    # Test configuration
    if command -v python3 &> /dev/null; then
        # Test imports
        if python3 -c "from linkedin_scraper.api.app import app; print('✅ App imports successfully')"; then
            success "Application imports successfully"
        else
            error "Application import failed. Please fix before deploying."
            exit 1
        fi
        
        # Run security tests if available
        if [ -f "quick_security_test.py" ]; then
            if python3 quick_security_test.py; then
                success "Security tests passed"
            else
                warning "Security tests failed. Please review before deploying."
            fi
        fi
    else
        warning "Python3 not found. Skipping pre-deployment tests."
    fi
}

# Deploy to App Engine
deploy_app_engine() {
    log "Deploying to App Engine..."
    
    # Use the updated app.yaml
    gcloud app deploy "${APP_YAML}.tmp" \
        --project="$PROJECT_ID" \
        --quiet \
        --promote
    
    success "Application deployed to App Engine"
    
    # Clean up temporary file
    rm -f "${APP_YAML}.tmp" "${APP_YAML}.tmp.bak"
}

# Set up Cloud Build trigger (optional)
setup_cloud_build() {
    if [ "$1" = "--setup-ci" ]; then
        log "Setting up Cloud Build trigger..."
        
        # This would typically be done through the console or with more specific configuration
        warning "Cloud Build trigger setup requires manual configuration."
        warning "Please set up a trigger in the Cloud Build console if you want CI/CD."
    fi
}

# Run post-deployment tests
post_deployment_tests() {
    log "Running post-deployment tests..."
    
    local app_url="https://${PROJECT_ID}.appspot.com"
    
    # Wait for deployment to be ready
    log "Waiting for deployment to be ready..."
    sleep 30
    
    # Test health endpoint
    if curl -f "$app_url/api/v1/health" > /dev/null 2>&1; then
        success "Health check passed: $app_url/api/v1/health"
    else
        error "Health check failed. Please check the logs."
        gcloud app logs tail -s default
        exit 1
    fi
    
    # Test web interface
    if curl -f "$app_url/" > /dev/null 2>&1; then
        success "Web interface accessible: $app_url"
    else
        warning "Web interface test failed. Please check manually."
    fi
    
    success "Post-deployment tests completed"
}

# Show deployment information
show_deployment_info() {
    local app_url="https://${PROJECT_ID}.appspot.com"
    
    log "Deployment completed successfully!"
    echo ""
    log "Application URLs:"
    log "  • Web Interface: $app_url"
    log "  • API Documentation: $app_url/api/docs"
    log "  • Health Check: $app_url/api/v1/health"
    echo ""
    log "Management Commands:"
    log "  • View logs: gcloud app logs tail -s default"
    log "  • View versions: gcloud app versions list"
    log "  • Scale service: gcloud app versions set-traffic default --splits=VERSION=1"
    echo ""
    log "Monitoring:"
    log "  • Cloud Console: https://console.cloud.google.com/appengine?project=$PROJECT_ID"
    log "  • Logs: https://console.cloud.google.com/logs?project=$PROJECT_ID"
    log "  • Monitoring: https://console.cloud.google.com/monitoring?project=$PROJECT_ID"
}

# Main deployment function
main() {
    log "Starting GCP deployment for LinkedIn Knowledge Management System..."
    
    check_prerequisites
    enable_apis
    create_app_engine
    create_storage_bucket
    setup_secrets
    update_app_yaml
    run_tests
    deploy_app_engine
    setup_cloud_build "$@"
    post_deployment_tests
    show_deployment_info
    
    success "GCP deployment completed successfully!"
}

# Help function
show_help() {
    echo "LinkedIn Knowledge Management System - GCP Deployment Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --setup-ci    Also set up Cloud Build CI/CD"
    echo "  --help        Show this help message"
    echo ""
    echo "Prerequisites:"
    echo "  • Google Cloud SDK installed and authenticated"
    echo "  • GCP project created and set as default"
    echo "  • Billing enabled on the project"
    echo ""
    echo "This script will:"
    echo "  • Enable required APIs"
    echo "  • Create App Engine application"
    echo "  • Set up Secret Manager"
    echo "  • Deploy the application"
    echo "  • Run post-deployment tests"
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