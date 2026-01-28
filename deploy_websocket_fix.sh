#!/bin/bash

# Deploy WebSocket fix to production
# This script MUST be run on the production server

set -e  # Exit on error

echo "========================================================================"
echo "WEBSOCKET FIX DEPLOYMENT"
echo "========================================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "takahe/asgi.py" ]; then
    echo -e "${RED}Error: Not in takahe project directory${NC}"
    echo "Please cd to your takahe installation first"
    exit 1
fi

# Function to run on production server
if [ "$1" == "--production" ]; then
    echo -e "${BLUE}Step 1:${NC} Checking current status..."
    echo "-----------------------------------"
    git status --short
    
    echo ""
    echo -e "${BLUE}Step 2:${NC} Pulling latest changes..."
    echo "-----------------------------------"
    git fetch origin
    
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    echo "Current branch: $CURRENT_BRANCH"
    
    git pull origin $CURRENT_BRANCH
    
    echo ""
    echo -e "${BLUE}Step 3:${NC} Verifying changes..."
    echo "-----------------------------------"
    
    # Check for single accept call
    accept_count=$(grep -c 'websocket.accept' api/websocket_streaming.py)
    if [ "$accept_count" -eq 1 ]; then
        echo -e "${GREEN}✓${NC} Single websocket.accept call - CORRECT"
    else
        echo -e "${RED}✗${NC} Multiple websocket.accept calls found: $accept_count"
        echo "This will cause 401 errors!"
        exit 1
    fi
    
    echo ""
    echo -e "${BLUE}Step 4:${NC} Stopping services..."
    echo "-----------------------------------"
    docker compose down
    
    echo ""
    echo -e "${BLUE}Step 5:${NC} Rebuilding containers..."
    echo "-----------------------------------"
    docker compose build --no-cache web
    
    echo ""
    echo -e "${BLUE}Step 6:${NC} Starting services..."
    echo "-----------------------------------"
    docker compose up -d
    
    echo ""
    echo -e "${BLUE}Step 7:${NC} Waiting for services to be ready..."
    echo "-----------------------------------"
    sleep 10
    
    echo ""
    echo -e "${BLUE}Step 8:${NC} Checking logs..."
    echo "-----------------------------------"
    echo "Showing last 50 lines of web container logs:"
    docker compose logs --tail=50 web
    
    echo ""
    echo -e "${GREEN}========================================================================"
    echo "DEPLOYMENT COMPLETE"
    echo "========================================================================${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Test WebSocket connection:"
    echo "     wss://social.manalejandro.com/api/v1/streaming?stream=user&access_token=YOUR_TOKEN"
    echo ""
    echo "  2. Watch logs in real-time:"
    echo "     docker compose logs -f web"
    echo ""
    echo "  3. Look for these messages when connecting:"
    echo "     [ASGI Router] Request type: websocket"
    echo "     Attempting to authenticate with token:"
    echo "     ✓ Token found:"
    echo "     ✓ Authenticated as:"
    echo ""
    
else
    # Instructions for running on production
    echo "This script must be run on your PRODUCTION server."
    echo ""
    echo -e "${YELLOW}Instructions:${NC}"
    echo ""
    echo "1. Push your local changes:"
    echo -e "   ${BLUE}git push origin feature/improve_security${NC}"
    echo ""
    echo "2. SSH to your production server:"
    echo -e "   ${BLUE}ssh your-server${NC}"
    echo ""
    echo "3. Navigate to takahe directory:"
    echo -e "   ${BLUE}cd /path/to/takahe${NC}"
    echo ""
    echo "4. Run this script with --production flag:"
    echo -e "   ${BLUE}bash deploy_websocket_fix.sh --production${NC}"
    echo ""
    echo "Or run commands manually:"
    echo -e "   ${BLUE}git pull origin feature/improve_security${NC}"
    echo -e "   ${BLUE}docker compose down${NC}"
    echo -e "   ${BLUE}docker compose build --no-cache web${NC}"
    echo -e "   ${BLUE}docker compose up -d${NC}"
    echo -e "   ${BLUE}docker compose logs -f web${NC}"
    echo ""
    echo "========================================================================"
fi
