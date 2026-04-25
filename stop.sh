#!/bin/bash
# Hermès Dashboard 停止脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "  Hermès Dashboard 停止脚本"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 从 PID 文件读取进程
if [ -f "$SCRIPT_DIR/.backend.pid" ]; then
    BACKEND_PID=$(cat "$SCRIPT_DIR/.backend.pid")
    if kill -0 $BACKEND_PID 2>/dev/null; then
        echo -e "${YELLOW}停止后端服务 (PID: $BACKEND_PID)...${NC}"
        kill $BACKEND_PID 2>/dev/null || true
        echo -e "${GREEN}✓ 后端已停止${NC}"
    else
        echo -e "${YELLOW}后端进程不存在或已停止${NC}"
    fi
    rm -f "$SCRIPT_DIR/.backend.pid"
else
    echo -e "${YELLOW}未找到后端 PID 文件${NC}"
fi

if [ -f "$SCRIPT_DIR/.frontend.pid" ]; then
    FRONTEND_PID=$(cat "$SCRIPT_DIR/.frontend.pid")
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        echo -e "${YELLOW}停止前端服务 (PID: $FRONTEND_PID)...${NC}"
        kill $FRONTEND_PID 2>/dev/null || true
        echo -e "${GREEN}✓ 前端已停止${NC}"
    else
        echo -e "${YELLOW}前端进程不存在或已停止${NC}"
    fi
    rm -f "$SCRIPT_DIR/.frontend.pid"
else
    echo -e "${YELLOW}未找到前端 PID 文件${NC}"
fi

# 清理残留的 uvicorn/vite 进程
echo -e "\n${YELLOW}检查残留进程...${NC}"
for proc in $(pgrep -f "uvicorn main:app" 2>/dev/null); do
    echo -e "${YELLOW}清理残留后端进程 (PID: $proc)${NC}"
    kill $proc 2>/dev/null || true
done

for proc in $(pgrep -f "vite" 2>/dev/null); do
    echo -e "${YELLOW}清理残留前端进程 (PID: $proc)${NC}"
    kill $proc 2>/dev/null || true
done

echo ""
echo "=========================================="
echo -e "${GREEN}  所有服务已停止${NC}"
echo "=========================================="
