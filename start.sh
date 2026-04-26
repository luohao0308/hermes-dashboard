#!/bin/bash
# Hermès Dashboard 启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "  Hermès Dashboard 启动脚本"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 Hermès Agent 是否运行
echo -e "\n${YELLOW}[1/3] 检查 Hermès Agent (localhost:9119)...${NC}"
if curl -s --max-time 2 http://localhost:9119/api/status > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Hermès Agent 运行中${NC}"
else
    echo -e "${RED}✗ Hermès Agent 未运行 (localhost:9119)${NC}"
    echo -e "${YELLOW}  请先启动 Hermès Agent: hermes dashboard${NC}"
    exit 1
fi

# 启动后端 (FastAPI)
echo -e "\n${YELLOW}[2/3] 启动后端服务 (port 8000)...${NC}"
cd "$SCRIPT_DIR/backend"

# 激活 Python 3.10 环境
source ~/opt/anaconda3/etc/profile.d/conda.sh
conda activate hermes310

# 检查后端依赖
if ! pip show fastapi > /dev/null 2>&1; then
    echo -e "${YELLOW}  安装后端依赖...${NC}"
    pip install -r requirements.txt -q
fi

# 启动后端 (后台运行)
python -m uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo $BACKEND_PID > "$SCRIPT_DIR/.backend.pid"
echo -e "${GREEN}✓ 后端已启动 (PID: $BACKEND_PID)${NC}"

# 等待后端就绪
sleep 2
if curl -s --max-time 5 http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 后端健康检查通过${NC}"
else
    echo -e "${YELLOW}⚠ 后端可能还未就绪，等待一下...${NC}"
    sleep 3
fi

# 启动前端 (Vite)
echo -e "\n${YELLOW}[3/3] 启动前端服务 (port 5173)...${NC}"
cd "$SCRIPT_DIR/frontend"

# 检查前端依赖
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}  安装前端依赖...${NC}"
    npm install --silent
fi

# 启动前端 (后台运行)
npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$SCRIPT_DIR/.frontend.pid"
echo -e "${GREEN}✓ 前端已启动 (PID: $FRONTEND_PID)${NC}"

# 等待前端就绪
sleep 3

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
