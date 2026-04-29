#!/bin/bash
# Hermès Dashboard 启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export PATH="/Applications/Codex.app/Contents/Resources:/opt/homebrew/bin:/usr/local/bin:$PATH"
export NO_PROXY="localhost,127.0.0.1,::1,${NO_PROXY:-}"
export no_proxy="localhost,127.0.0.1,::1,${no_proxy:-}"

echo "=========================================="
echo "  Hermès Dashboard 启动脚本"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

port_in_use() {
    local port="$1"
    lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
}

require_port_free() {
    local port="$1"
    local label="$2"
    if port_in_use "$port"; then
        echo -e "${RED}✗ ${label}端口 $port 已被占用，请先运行 ./stop.sh 或手动释放端口${NC}"
        lsof -nP -iTCP:"$port" -sTCP:LISTEN || true
        exit 1
    fi
}

# 检查 Hermès Agent 是否运行
echo -e "\n${YELLOW}[1/3] 检查 Hermès Agent (localhost:9119)...${NC}"
if curl --noproxy '*' -fsS --max-time 2 http://localhost:9119/api/status > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Hermès Agent 运行中${NC}"
else
    echo -e "${YELLOW}⚠ Hermès Agent 未运行 (localhost:9119)${NC}"
    echo -e "${YELLOW}  Dashboard 会以降级模式启动；任务/日志等代理数据需先运行: hermes dashboard${NC}"
fi

# 启动后端 (FastAPI)
echo -e "\n${YELLOW}[2/3] 启动后端服务 (port 8000)...${NC}"
require_port_free 8000 "后端"
cd "$SCRIPT_DIR/backend"

PYTHON_CMD=""
if [ -f "$HOME/opt/anaconda3/etc/profile.d/conda.sh" ]; then
    # shellcheck disable=SC1091
    source "$HOME/opt/anaconda3/etc/profile.d/conda.sh"
    if conda env list | awk '{print $1}' | grep -qx "hermes310"; then
        conda activate hermes310
        PYTHON_CMD="python"
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_CMD="$(command -v python3)"
    elif command -v python >/dev/null 2>&1; then
        PYTHON_CMD="$(command -v python)"
    else
        echo -e "${RED}✗ 未找到 Python，请安装 Python 3.10+${NC}"
        exit 1
    fi
fi

PYTHON_OK="$("$PYTHON_CMD" - <<'PY'
import sys
print("1" if sys.version_info >= (3, 10) else "0")
PY
)"
if [ "$PYTHON_OK" != "1" ]; then
    echo -e "${RED}✗ 当前 Python 版本过低: $("$PYTHON_CMD" --version 2>&1)，需要 3.10+${NC}"
    exit 1
fi

# 检查后端依赖
if ! "$PYTHON_CMD" -m pip show fastapi > /dev/null 2>&1; then
    echo -e "${YELLOW}  安装后端依赖...${NC}"
    "$PYTHON_CMD" -m pip install -r requirements.txt -q
fi

# 启动后端 (后台运行)
nohup "$PYTHON_CMD" -m uvicorn main:app --host 0.0.0.0 --port 8000 > "$SCRIPT_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$SCRIPT_DIR/.backend.pid"
echo -e "${GREEN}✓ 后端已启动 (PID: $BACKEND_PID)${NC}"

# 等待后端就绪
sleep 2
if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo -e "${RED}✗ 后端启动失败，请检查 8000 端口是否被占用${NC}"
    rm -f "$SCRIPT_DIR/.backend.pid"
    exit 1
fi

BACKEND_READY=0
for _ in {1..15}; do
    if curl --noproxy '*' -fsS --max-time 2 http://localhost:8000/health > /dev/null 2>&1; then
        BACKEND_READY=1
        break
    fi
    sleep 1
done

if [ "$BACKEND_READY" -eq 1 ]; then
    echo -e "${GREEN}✓ 后端健康检查通过${NC}"
else
    echo -e "${RED}✗ 后端健康检查失败${NC}"
    kill "$BACKEND_PID" 2>/dev/null || true
    rm -f "$SCRIPT_DIR/.backend.pid"
    exit 1
fi

# 启动前端 (Vite)
echo -e "\n${YELLOW}[3/3] 启动前端服务 (port 5173)...${NC}"
require_port_free 5173 "前端"
cd "$SCRIPT_DIR/frontend"

if ! command -v npm >/dev/null 2>&1; then
    echo -e "${RED}✗ 未找到 npm，请安装 Node.js 20+ / npm${NC}"
    exit 1
fi

NODE_MAJOR="$(node -p "Number(process.versions.node.split('.')[0])" 2>/dev/null || echo 0)"
if [ "$NODE_MAJOR" -lt 20 ]; then
    echo -e "${RED}✗ 当前 Node.js 版本过低: $(node --version 2>/dev/null || echo unknown)，需要 20+${NC}"
    exit 1
fi

# 检查前端依赖
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}  安装前端依赖...${NC}"
    npm install --silent
fi

# 启动前端 (后台运行)
nohup npm run dev -- --host 0.0.0.0 --strictPort > "$SCRIPT_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$SCRIPT_DIR/.frontend.pid"
echo -e "${GREEN}✓ 前端已启动 (PID: $FRONTEND_PID)${NC}"

# 等待前端就绪
sleep 3
if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
    echo -e "${RED}✗ 前端启动失败，请检查 5173 端口是否被占用${NC}"
    rm -f "$SCRIPT_DIR/.frontend.pid"
    exit 1
fi

FRONTEND_READY=0
for _ in {1..10}; do
    if curl --noproxy '*' -fsS --max-time 2 http://localhost:5173/ > /dev/null 2>&1; then
        FRONTEND_READY=1
        break
    fi
    sleep 1
done

if [ "$FRONTEND_READY" -eq 1 ]; then
    echo -e "${GREEN}✓ 前端健康检查通过${NC}"
else
    echo -e "${RED}✗ 前端健康检查失败${NC}"
    kill "$FRONTEND_PID" 2>/dev/null || true
    rm -f "$SCRIPT_DIR/.frontend.pid"
    exit 1
fi

echo ""
echo "=========================================="
echo -e "${GREEN}  全部服务已启动!${NC}"
echo "=========================================="
echo ""
echo "  Hermès Dashboard:  http://localhost:5173"
echo "  Backend API:       http://localhost:8000"
echo "  Backend Health:    http://localhost:8000/health"
echo "  Hermès API:        http://localhost:9119"
echo ""
echo "  停止服务: ./stop.sh"
echo "=========================================="
