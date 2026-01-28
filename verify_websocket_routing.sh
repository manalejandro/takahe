#!/bin/bash

echo "========================================================================"
echo "WEBSOCKET ROUTING VERIFICATION"
echo "========================================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

errors=0
warnings=0

echo "1. Checking for duplicate routes to /api/v1/streaming..."
echo "-----------------------------------"

# Check if api/urls.py has the streaming route (should NOT exist)
if grep -q 'path("v1/streaming".*streaming\.streaming' api/urls.py; then
    echo -e "${RED}✗ CRITICAL: api/urls.py still has HTTP route for v1/streaming${NC}"
    echo "  This will intercept WebSocket connections and cause 401!"
    echo "  The route should ONLY be handled by asgi.py"
    errors=$((errors + 1))
else
    echo -e "${GREEN}✓${NC} api/urls.py does NOT have conflicting HTTP route"
fi

# Check that health endpoint exists
if grep -q 'path("v1/streaming/health"' api/urls.py; then
    echo -e "${GREEN}✓${NC} Health check endpoint exists"
else
    echo -e "${YELLOW}⚠${NC}  Health check endpoint not found (not critical)"
    warnings=$((warnings + 1))
fi

echo ""
echo "2. Checking ASGI router..."
echo "-----------------------------------"

# Check that asgi.py handles streaming endpoint
if grep -q 'if path == "/api/v1/streaming"' takahe/asgi.py; then
    echo -e "${GREEN}✓${NC} ASGI router checks for /api/v1/streaming"
else
    echo -e "${RED}✗ CRITICAL: ASGI router doesn't check streaming path${NC}"
    errors=$((errors + 1))
fi

# Check for WebSocket handler call
if grep -q 'await streaming_websocket' takahe/asgi.py; then
    echo -e "${GREEN}✓${NC} ASGI router calls streaming_websocket handler"
else
    echo -e "${RED}✗ CRITICAL: ASGI router doesn't call WebSocket handler${NC}"
    errors=$((errors + 1))
fi

# Check for inspection of Upgrade header
if grep -q 'upgrade.*websocket' takahe/asgi.py; then
    echo -e "${GREEN}✓${NC} ASGI router checks for Upgrade header"
else
    echo -e "${YELLOW}⚠${NC}  ASGI router might not detect WebSocket upgrade requests"
    warnings=$((warnings + 1))
fi

echo ""
echo "3. Checking WebSocket handler..."
echo "-----------------------------------"

# Check for single accept
accept_count=$(grep -c 'type.*:.*websocket\.accept' api/websocket_streaming.py)
if [ "$accept_count" -eq 1 ]; then
    echo -e "${GREEN}✓${NC} WebSocket handler has single accept call"
elif [ "$accept_count" -eq 0 ]; then
    echo -e "${RED}✗ CRITICAL: No websocket.accept found${NC}"
    errors=$((errors + 1))
else
    echo -e "${RED}✗ CRITICAL: Multiple websocket.accept calls ($accept_count)${NC}"
    echo "  This will cause connection errors!"
    errors=$((errors + 1))
fi

# Check that accept is early
first_accept_line=$(grep -n 'type.*:.*websocket\.accept' api/websocket_streaming.py | head -1 | cut -d: -f1)
if [ -n "$first_accept_line" ] && [ "$first_accept_line" -lt 60 ]; then
    echo -e "${GREEN}✓${NC} WebSocket accepted early (line $first_accept_line)"
else
    echo -e "${YELLOW}⚠${NC}  WebSocket accept might be too late (line $first_accept_line)"
    warnings=$((warnings + 1))
fi

echo ""
echo "4. Checking nginx configuration..."
echo "-----------------------------------"

if grep -A 5 'location /api/v1/streaming' docker/nginx.conf.d/default.conf.tpl | grep -q 'proxy_set_header Upgrade'; then
    echo -e "${GREEN}✓${NC} Nginx configured for WebSocket upgrade"
else
    echo -e "${RED}✗ CRITICAL: Nginx not configured for WebSocket${NC}"
    errors=$((errors + 1))
fi

echo ""
echo "========================================================================"
echo "VERIFICATION RESULTS"
echo "========================================================================"
echo ""

if [ $errors -eq 0 ]; then
    echo -e "${GREEN}✓ ALL CRITICAL CHECKS PASSED!${NC}"
    if [ $warnings -gt 0 ]; then
        echo -e "${YELLOW}  ($warnings warning(s) found)${NC}"
    fi
    echo ""
    echo "The WebSocket routing is correctly configured."
    echo ""
    echo "Next steps:"
    echo "  1. Commit and push changes:"
    echo "     git add -A"
    echo "     git commit -m 'Fix: Remove HTTP route conflict for WebSocket streaming'"
    echo "     git push"
    echo ""
    echo "  2. Deploy to production:"
    echo "     ssh production-server"
    echo "     cd /path/to/takahe"
    echo "     git pull"
    echo "     docker compose restart web"
    echo ""
    echo "  3. Test with test_websocket.html"
    echo ""
    exit 0
else
    echo -e "${RED}✗ $errors CRITICAL ERROR(S) FOUND!${NC}"
    if [ $warnings -gt 0 ]; then
        echo -e "${YELLOW}  ($warnings warning(s) found)${NC}"
    fi
    echo ""
    echo "Please fix the errors above before deploying."
    echo ""
    exit 1
fi
