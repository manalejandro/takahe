#!/bin/bash

echo "========================================================================"
echo "WEBSOCKET DIAGNOSTIC SCRIPT"
echo "========================================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "1. Checking ASGI configuration..."
echo "-----------------------------------"
if [ -f "takahe/asgi.py" ]; then
    echo -e "${GREEN}✓${NC} asgi.py exists"
    if grep -q "streaming_websocket" takahe/asgi.py; then
        echo -e "${GREEN}✓${NC} WebSocket handler imported in asgi.py"
    else
        echo -e "${RED}✗${NC} WebSocket handler NOT found in asgi.py"
    fi
    
    if grep -q 'scope\["type"\] == "websocket"' takahe/asgi.py; then
        echo -e "${GREEN}✓${NC} WebSocket routing logic present"
    else
        echo -e "${RED}✗${NC} WebSocket routing logic NOT found"
    fi
else
    echo -e "${RED}✗${NC} asgi.py NOT found"
fi

echo ""
echo "2. Checking WebSocket streaming implementation..."
echo "-----------------------------------"
if [ -f "api/websocket_streaming.py" ]; then
    echo -e "${GREEN}✓${NC} websocket_streaming.py exists"
    
    # Check for immediate accept
    if grep -q 'await send.*websocket.accept' api/websocket_streaming.py | head -1; then
        echo -e "${GREEN}✓${NC} WebSocket accept call found"
        
        # Check if accept is at the beginning
        accept_line=$(grep -n 'await send.*websocket.accept' api/websocket_streaming.py | head -1 | cut -d: -f1)
        if [ "$accept_line" -lt 50 ]; then
            echo -e "${GREEN}✓${NC} WebSocket accepted early (line $accept_line) - GOOD"
        else
            echo -e "${YELLOW}⚠${NC}  WebSocket accepted late (line $accept_line) - should be earlier"
        fi
        
        # Check for duplicate accepts
        accept_count=$(grep -c 'websocket.accept' api/websocket_streaming.py)
        if [ "$accept_count" -eq 1 ]; then
            echo -e "${GREEN}✓${NC} Single accept call - CORRECT"
        else
            echo -e "${RED}✗${NC} Multiple accept calls ($accept_count found) - THIS WILL CAUSE 401!"
        fi
    else
        echo -e "${RED}✗${NC} No websocket.accept call found"
    fi
    
    # Check for token extraction
    if grep -q 'access_token.*=.*params\.get' api/websocket_streaming.py; then
        echo -e "${GREEN}✓${NC} Token extraction from query string present"
    else
        echo -e "${YELLOW}⚠${NC}  Token extraction might be missing"
    fi
else
    echo -e "${RED}✗${NC} websocket_streaming.py NOT found"
fi

echo ""
echo "3. Checking if server is running with ASGI (uvicorn)..."
echo "-----------------------------------"
if [ -f "Procfile" ]; then
    if grep -q "uvicorn takahe.asgi:application" Procfile; then
        echo -e "${GREEN}✓${NC} Procfile uses uvicorn with asgi.py"
    else
        echo -e "${YELLOW}⚠${NC}  Procfile might not be using uvicorn"
        grep "^web:" Procfile
    fi
fi

if [ -f "docker/run.sh" ]; then
    if grep -q "uvicorn takahe.asgi:application" docker/run.sh; then
        echo -e "${GREEN}✓${NC} docker/run.sh uses uvicorn with asgi.py"
    else
        echo -e "${YELLOW}⚠${NC}  docker/run.sh might not be using uvicorn"
    fi
fi

echo ""
echo "4. Checking nginx configuration..."
echo "-----------------------------------"
if [ -f "docker/nginx.conf.d/default.conf.tpl" ]; then
    echo -e "${GREEN}✓${NC} nginx config template exists"
    
    if grep -q "location /api/v1/streaming" docker/nginx.conf.d/default.conf.tpl; then
        echo -e "${GREEN}✓${NC} Streaming location block found"
        
        if grep -A 10 "location /api/v1/streaming" docker/nginx.conf.d/default.conf.tpl | grep -q "proxy_set_header Upgrade"; then
            echo -e "${GREEN}✓${NC} Upgrade header configured"
        else
            echo -e "${RED}✗${NC} Missing Upgrade header - WEBSOCKET WON'T WORK!"
        fi
        
        if grep -A 10 "location /api/v1/streaming" docker/nginx.conf.d/default.conf.tpl | grep -q 'Connection.*upgrade'; then
            echo -e "${GREEN}✓${NC} Connection upgrade configured"
        else
            echo -e "${RED}✗${NC} Missing Connection header - WEBSOCKET WON'T WORK!"
        fi
    else
        echo -e "${RED}✗${NC} No specific location for /api/v1/streaming"
    fi
fi

echo ""
echo "5. Recent commits..."
echo "-----------------------------------"
git log --oneline -3

echo ""
echo "========================================================================"
echo "SUMMARY"
echo "========================================================================"
echo ""
echo "If you see ${RED}✗${NC} or ${YELLOW}⚠${NC} above, those are potential issues."
echo ""
echo "Next steps:"
echo "  1. If code looks correct but still 401:"
echo "     - Restart your production server"
echo "     - Check production nginx config (not just the template)"
echo "     - Clear browser cache and try again"
echo ""
echo "  2. To test in production, check logs for:"
echo "     [ASGI Router] Request type: websocket"
echo "     Attempting to authenticate with token:"
echo ""
echo "  3. If you don't see those logs, the WebSocket request"
echo "     is being rejected before reaching your code."
echo ""
echo "========================================================================"
