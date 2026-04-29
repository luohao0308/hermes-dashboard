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

stop_pid() {
    local pid="$1"
    local label="$2"
    if kill -0 "$pid" 2>/dev/null; then
        echo -e "${YELLOW}停止${label} (PID: $pid)...${NC}"
        kill "$pid" 2>/dev/null || true
        for _ in {1..10}; do
            if ! kill -0 "$pid" 2>/dev/null; then
                echo -e "${GREEN}✓ ${label}已停止${NC}"
                return
            fi
            sleep 0.3
        done
        echo -e "${YELLOW}${label}未及时退出，强制停止 (PID: $pid)...${NC}"
        kill -9 "$pid" 2>/dev/null || true
        echo -e "${GREEN}✓ ${label}已停止${NC}"
    else
        echo -e "${YELLOW}${label}进程不存在或已停止${NC}"
    fi
}

# 从 PID 文件读取进程
if [ -f "$SCRIPT_DIR/.backend.pid" ]; then
    BACKEND_PID=$(cat "$SCRIPT_DIR/.backend.pid")
    stop_pid "$BACKEND_PID" "后端服务"
    rm -f "$SCRIPT_DIR/.backend.pid"
else
    echo -e "${YELLOW}未找到后端 PID 文件${NC}"
fi

if [ -f "$SCRIPT_DIR/.frontend.pid" ]; then
    FRONTEND_PID=$(cat "$SCRIPT_DIR/.frontend.pid")
    stop_pid "$FRONTEND_PID" "前端服务"
    rm -f "$SCRIPT_DIR/.frontend.pid"
else
    echo -e "${YELLOW}未找到前端 PID 文件${NC}"
fi

# 清理残留的 uvicorn/vite 进程
echo -e "\n${YELLOW}检查残留进程...${NC}"
for proc in $(pgrep -f "uvicorn main:app" 2>/dev/null); do
    stop_pid "$proc" "残留后端进程"
done

for proc in $(pgrep -f "vite" 2>/dev/null); do
    stop_pid "$proc" "残留前端进程"
done

echo ""
echo "=========================================="
echo -e "${GREEN}  所有服务已停止${NC}"
echo "=========================================="
