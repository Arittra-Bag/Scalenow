#!/bin/bash
# LinkedIn Knowledge Management System - Health Check Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEFAULT_URL="http://localhost:8000"
TIMEOUT=10
VERBOSE=false

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

# Health check function
check_health() {
    local url="$1"
    local endpoint="$2"
    local description="$3"
    
    if [ "$VERBOSE" = true ]; then
        log "Checking $description at $url$endpoint"
    fi
    
    local response
    local status_code
    
    # Make request and capture response
    response=$(curl -s -w "\n%{http_code}" --max-time "$TIMEOUT" "$url$endpoint" 2>/dev/null)
    status_code=$(echo "$response" | tail -n1)
    response_body=$(echo "$response" | head -n -1)
    
    if [ "$status_code" = "200" ]; then
        success "$description: OK"
        if [ "$VERBOSE" = true ]; then
            echo "Response: $response_body"
        fi
        return 0
    else
        error "$description: FAILED (HTTP $status_code)"
        if [ "$VERBOSE" = true ]; then
            echo "Response: $response_body"
        fi
        return 1
    fi
}

# Comprehensive health check
run_health_checks() {
    local base_url="$1"
    local failed_checks=0
    
    log "Running health checks for LinkedIn Knowledge Management System"
    log "Base URL: $base_url"
    echo ""
    
    # Basic health check
    if ! check_health "$base_url" "/api/v1/health" "API Health Check"; then
        ((failed_checks++))
    fi
    
    # Web interface check
    if ! check_health "$base_url" "/" "Web Interface"; then
        ((failed_checks++))
    fi
    
    # API documentation check
    if ! check_health "$base_url" "/api/docs" "API Documentation"; then
        ((failed_checks++))
    fi
    
    # Queue status check
    if ! check_health "$base_url" "/api/v1/queue/status" "Queue Status"; then
        ((failed_checks++))
    fi
    
    # Knowledge endpoint check
    if ! check_health "$base_url" "/api/v1/knowledge" "Knowledge API"; then
        ((failed_checks++))
    fi
    
    # Analytics endpoint check
    if ! check_health "$base_url" "/api/v1/analytics/content" "Analytics API"; then
        ((failed_checks++))
    fi
    
    echo ""
    
    if [ $failed_checks -eq 0 ]; then
        success "All health checks passed! ✅"
        return 0
    else
        error "$failed_checks health check(s) failed! ❌"
        return 1
    fi
}

# Detailed system check
run_detailed_checks() {
    local base_url="$1"
    
    log "Running detailed system checks..."
    echo ""
    
    # Check if we can get detailed health info
    local health_response
    health_response=$(curl -s --max-time "$TIMEOUT" "$base_url/api/v1/health" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        log "System Information:"
        echo "$health_response" | python3 -m json.tool 2>/dev/null || echo "$health_response"
        echo ""
    fi
    
    # Check queue status
    local queue_response
    queue_response=$(curl -s --max-time "$TIMEOUT" "$base_url/api/v1/queue/status" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        log "Queue Status:"
        echo "$queue_response" | python3 -m json.tool 2>/dev/null || echo "$queue_response"
        echo ""
    fi
    
    # Check analytics
    local analytics_response
    analytics_response=$(curl -s --max-time "$TIMEOUT" "$base_url/api/v1/analytics/content" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        log "Analytics Summary:"
        echo "$analytics_response" | python3 -m json.tool 2>/dev/null || echo "$analytics_response"
        echo ""
    fi
}

# Monitor mode - continuous health checking
monitor_mode() {
    local base_url="$1"
    local interval="${2:-30}"
    
    log "Starting health monitoring (checking every ${interval}s)"
    log "Press Ctrl+C to stop"
    echo ""
    
    while true; do
        local timestamp=$(date +'%Y-%m-%d %H:%M:%S')
        
        if run_health_checks "$base_url" > /dev/null 2>&1; then
            echo "[$timestamp] ✅ All systems healthy"
        else
            echo "[$timestamp] ❌ Health check failed"
            # Run detailed check on failure
            run_health_checks "$base_url"
        fi
        
        sleep "$interval"
    done
}

# Show help
show_help() {
    echo "LinkedIn Knowledge Management System - Health Check Script"
    echo ""
    echo "Usage: $0 [OPTIONS] [URL]"
    echo ""
    echo "Options:"
    echo "  -v, --verbose     Show detailed output"
    echo "  -t, --timeout N   Set timeout in seconds (default: 10)"
    echo "  -d, --detailed    Run detailed system checks"
    echo "  -m, --monitor N   Monitor mode - check every N seconds (default: 30)"
    echo "  -h, --help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Check localhost:8000"
    echo "  $0 https://myapp.onrender.com        # Check remote deployment"
    echo "  $0 -v -d http://localhost:8000       # Verbose detailed check"
    echo "  $0 -m 60 http://localhost:8000       # Monitor every 60 seconds"
}

# Parse command line arguments
URL="$DEFAULT_URL"
DETAILED=false
MONITOR=false
MONITOR_INTERVAL=30

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -d|--detailed)
            DETAILED=true
            shift
            ;;
        -m|--monitor)
            MONITOR=true
            if [[ $2 =~ ^[0-9]+$ ]]; then
                MONITOR_INTERVAL="$2"
                shift 2
            else
                shift
            fi
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        http*://*)
            URL="$1"
            shift
            ;;
        *)
            error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main execution
main() {
    # Check if curl is available
    if ! command -v curl &> /dev/null; then
        error "curl is not installed. Please install curl to run health checks."
        exit 1
    fi
    
    if [ "$MONITOR" = true ]; then
        monitor_mode "$URL" "$MONITOR_INTERVAL"
    elif [ "$DETAILED" = true ]; then
        run_health_checks "$URL"
        echo ""
        run_detailed_checks "$URL"
    else
        run_health_checks "$URL"
    fi
}

# Run main function
main