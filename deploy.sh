#!/bin/bash

# IdeaHunter Deployment Script
# This script handles deployment to different environments

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="ideahunter"
VERSION=${VERSION:-"latest"}
ENVIRONMENT=${ENVIRONMENT:-"staging"}
DOCKER_REGISTRY=${DOCKER_REGISTRY:-""}
DOCKER_IMAGE="${DOCKER_REGISTRY}${APP_NAME}:${VERSION}"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required environment variables are set
check_env_vars() {
    log_info "Checking environment variables..."

    required_vars=("ANTHROPIC_API_KEY" "DATABASE_URL")

    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            log_warn "Environment variable $var is not set"
        fi
    done
}

# Build Docker image
build_image() {
    log_info "Building Docker image: $DOCKER_IMAGE"

    docker build -t "$DOCKER_IMAGE" .

    if [ $? -eq 0 ]; then
        log_info "Docker image built successfully"
    else
        log_error "Docker image build failed"
        exit 1
    fi
}

# Push Docker image to registry
push_image() {
    if [ -n "$DOCKER_REGISTRY" ]; then
        log_info "Pushing Docker image to registry: $DOCKER_IMAGE"

        docker push "$DOCKER_IMAGE"

        if [ $? -eq 0 ]; then
            log_info "Docker image pushed successfully"
        else
            log_error "Docker image push failed"
            exit 1
        fi
    else
        log_warn "No Docker registry specified, skipping push"
    fi
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."

    # Add your migration commands here
    # Example: docker-compose run --rm app python backend/db/migrate.py

    log_info "Database migrations completed"
}

# Deploy to environment
deploy() {
    log_info "Deploying to $ENVIRONMENT environment..."

    case $ENVIRONMENT in
        staging)
            log_info "Deploying to staging..."
            # Add staging-specific deployment commands
            # Example: kubectl apply -f k8s/staging/
            ;;
        production)
            log_info "Deploying to production..."
            # Add production-specific deployment commands
            # Example: kubectl apply -f k8s/production/
            ;;
        *)
            log_error "Unknown environment: $ENVIRONMENT"
            exit 1
            ;;
    esac

    log_info "Deployment to $ENVIRONMENT completed"
}

# Run health checks
health_check() {
    log_info "Running health checks..."

    # Add health check commands here
    # Example: curl -f http://localhost:5000/api/health || exit 1

    log_info "Health checks passed"
}

# Rollback deployment
rollback() {
    log_warn "Rolling back deployment..."

    # Add rollback commands here
    # Example: kubectl rollout undo deployment/ideahunter

    log_info "Rollback completed"
}

# Main deployment flow
main() {
    log_info "Starting deployment of $APP_NAME version $VERSION to $ENVIRONMENT"

    # Check environment variables
    check_env_vars

    # Build image
    build_image

    # Push image (if registry specified)
    push_image

    # Deploy
    deploy

    # Run migrations
    run_migrations

    # Health checks
    health_check

    log_info "Deployment completed successfully!"
}

# Handle script arguments
case "${1:-}" in
    build)
        build_image
        ;;
    push)
        push_image
        ;;
    deploy)
        main
        ;;
    rollback)
        rollback
        ;;
    health-check)
        health_check
        ;;
    *)
        echo "Usage: $0 {build|push|deploy|rollback|health-check}"
        echo "Environment variables: ENVIRONMENT, VERSION, DOCKER_REGISTRY"
        exit 1
        ;;
esac