# 发布检查清单 (Pre-Launch Checklist)

> 基于 `shipping-and-launch` + `security-and-hardening` skill 整理。
> 每次发布前逐项确认，所有项必须 green 才能合并到 main。

---

## 代码质量

- [ ] 所有单元测试通过 (`npm run test:unit` + `pytest tests/backend/`)
- [ ] 构建成功无警告 (`npm run build` + `uvicorn main:app --reload` 能启动)
- [ ] Lint 和类型检查通过 (`npm run lint` + `vue-tsc --noEmit`)
- [ ] 代码已 review 并 approved（PR 至少 1 个 approval）
- [ ] 无 TODO 注释应在此阶段解决
- [ ] 无 `console.log` 调试语句（生产代码）
- [ ] 错误处理覆盖预期失败场景

## 安全

- [ ] `.env` 中无真实 secret（API key、password 等）
- [ ] `npm audit --audit-level=high` 无 critical/high 漏洞
- [ ] 所有用户输入在边界处验证（Query/Body 参数有类型和范围限制）
- [ ] CORS  origins 非 `*`（生产环境需指定具体域名）
- [ ] 安全响应头已配置（X-Frame-Options, X-Content-Type-Options 等）
- [ ] Rate Limiting 已启用（SSE 端点 30/min，其他端点 100/min）
- [ ] 无内网地址或凭证在错误响应中暴露（HTTPException detail 不过度详细）
- [ ] 前端无敏感信息在 localStorage（auth token 等）

## 性能

- [ ] Core Web Vitals 阈值：
  - LCP ≤ 2500ms
  - INP ≤ 200ms
  - CLS ≤ 0.1
- [ ] Bundle 分 chunk（naive-ui 独立、xterm 独立），无单文件 > 500KB
- [ ] 构建产物 gzip 比例合理（xterm 334KB → 84KB gzip）
- [ ] 无 N+1 查询问题
- [ ] 图片有尺寸属性（防止 CLS）

## 基础设施

- [ ] 环境变量在生产环境正确设置（.env.example 已更新）
- [ ] 数据库 migrations 就绪（如有）
- [ ] Health check endpoint 返回 200
- [ ] 日志和错误上报已配置
- [ ] CDN/静态资源缓存已配置

## 文档

- [ ] README 更新（新功能说明、依赖变更）
- [ ] CHANGELOG 更新（如有）
- [ ] API 文档同步（如有）

## 部署

- [ ] 已在 staging 环境验证
- [ ] 回滚方案已准备（上一个稳定版本的 commit/tag）
- [ ] 团队已通知部署时间窗口
- [ ] 部署后监控指标基线已记录

---

## 快速检查命令

```bash
# 前端
cd frontend
npm run lint          # ESLint
npx vue-tsc --noEmit  # 类型检查
npm run test:unit     # 单元测试
npm run build         # 构建
npm audit --audit-level=high  # 安全审计

# 后端
cd backend
flake8 . --select=E9,F63,F7,F82  # 致命错误
pytest tests/ -v                  # 测试
python -m py_compile main.py      # 语法检查
```

## Rollback 方案

如果发布后指标异常（错误率 > 2x 基线、p95 延迟 > 50% 增长）：

```bash
# 方案 A：feature flag 关闭（< 1 分钟）
# 方案 B：git revert 并重新部署（< 5 分钟）
git revert <commit-hash>
git push
# 触发 CI/CD 重新部署

# 方案 C：切换到上一个 tag（< 5 分钟）
git checkout <previous-tag>
docker build && docker push
```
