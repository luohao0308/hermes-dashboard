"""Agent config loader — reads/writes YAML config for agent settings."""

import os
from pathlib import Path
from typing import Any

import yaml

CONFIG_PATH = Path(__file__).parent / "agents.yaml"


def get_default_config() -> dict[str, Any]:
    return {
        "main_agent": "dispatcher",
        "agents": {
            "dispatcher": {
                "name": "Dispatcher",
                "description": "分发任务到合适的 Agent",
                "instructions": "你是一个任务分发员。理解用户需求后，决定调用哪个专业 Agent。",
                "enabled": True,
            },
            "researcher": {
                "name": "Researcher",
                "description": "深入研究问题，搜索信息，分析数据",
                "instructions": "你是一个专业研究员。使用搜索工具深入分析问题，提供结构化的研究报告。",
                "enabled": True,
            },
            "developer": {
                "name": "Developer",
                "description": "编写和调试代码，实现功能",
                "instructions": "你是一个专业开发者。编写高质量代码，进行调试和优化。",
                "enabled": True,
            },
            "reviewer": {
                "name": "Reviewer",
                "description": "审查代码质量，发现问题，给出改进建议",
                "instructions": "你是一个专业代码审查员。审查代码质量、安全性和可维护性。",
                "enabled": True,
            },
            "tester": {
                "name": "Tester",
                "description": "编写测试用例，验证功能正确性",
                "instructions": "你是一个专业测试工程师。设计测试用例，验证功能正确性。",
                "enabled": True,
            },
            "devops": {
                "name": "DevOps",
                "description": "自动化部署、CI/CD、基础设施管理",
                "instructions": "你是一个专业 DevOps 工程师。负责自动化部署和基础设施管理。",
                "enabled": True,
            },
        },
        "custom_agents": [],
    }


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        cfg = get_default_config()
        save_config(cfg)
        return cfg
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_config(cfg: dict[str, Any]) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, default_flow_style=False)
