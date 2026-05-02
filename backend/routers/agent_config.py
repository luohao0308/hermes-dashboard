"""Agent configuration CRUD endpoints."""

import json
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from agent.config_loader import load_config, save_config
from agent.agent_manager import reload_agents
from agent.config_evaluator import compare_agent_config, evaluate_agent_config
from agent.config_history import config_history

router = APIRouter()


class AgentToggle(BaseModel):
    enabled: bool


class SetMainRequest(BaseModel):
    main_agent: str


class CustomAgentCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    instructions: Optional[str] = ""
    enabled: bool = True


class ConfigCompareRequest(BaseModel):
    main_agent: Optional[str] = None
    enabled_overrides: dict[str, bool] = {}


@router.get("/api/agent/config")
async def get_agent_config():
    cfg = load_config()
    return {
        "main_agent": cfg.get("main_agent"),
        "agents": cfg.get("agents", {}),
        "custom_agents": cfg.get("custom_agents", []),
        "evaluation": evaluate_agent_config(cfg),
    }


@router.get("/api/agent/config/history")
async def get_agent_config_history(limit: int = Query(20, ge=1, le=100)):
    return {"events": config_history.list_events(limit=limit)}


@router.post("/api/agent/config/compare")
async def compare_agent_config_endpoint(body: ConfigCompareRequest):
    cfg = load_config()
    return compare_agent_config(cfg, body.dict())


@router.put("/api/agent/config/enabled")
async def toggle_agent(name: str, body: AgentToggle):
    cfg = load_config()
    before = json.loads(json.dumps(cfg))
    if name in cfg["agents"]:
        cfg["agents"][name]["enabled"] = body.enabled
    else:
        for ca in cfg.get("custom_agents", []):
            if ca["name"].lower().replace(" ", "_") == name:
                ca["enabled"] = body.enabled
                break
        else:
            raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")
    save_config(cfg)
    config_history.record("toggle_agent", before, cfg, target=name)
    reload_agents()
    return {"ok": True, "agent": name, "enabled": body.enabled}


@router.post("/api/agent/config/main")
async def set_main_agent(body: SetMainRequest):
    cfg = load_config()
    before = json.loads(json.dumps(cfg))
    key = body.main_agent
    if key not in cfg["agents"] and not any(
        c["name"].lower().replace(" ", "_") == key for c in cfg.get("custom_agents", [])
    ):
        raise HTTPException(status_code=404, detail=f"Agent '{key}' not found")
    cfg["main_agent"] = key
    save_config(cfg)
    config_history.record("set_main_agent", before, cfg, target=key)
    reload_agents()
    return {"ok": True, "main_agent": key}


@router.post("/api/agent/config/custom")
async def add_custom_agent(body: CustomAgentCreate):
    cfg = load_config()
    before = json.loads(json.dumps(cfg))
    key = body.name.lower().replace(" ", "_")
    if key in cfg["agents"] or any(
        c["name"].lower().replace(" ", "_") == key for c in cfg.get("custom_agents", [])
    ):
        raise HTTPException(status_code=409, detail=f"Agent '{key}' already exists")
    cfg.setdefault("custom_agents", []).append({
        "name": body.name,
        "description": body.description,
        "instructions": body.instructions or f"You are {body.name}.",
        "enabled": body.enabled,
    })
    save_config(cfg)
    config_history.record("add_custom_agent", before, cfg, target=key)
    reload_agents()
    return {"ok": True, "agent": key}


@router.delete("/api/agent/config/custom/{agent_key}")
async def delete_custom_agent(agent_key: str):
    cfg = load_config()
    before = json.loads(json.dumps(cfg))
    original_len = len(cfg.get("custom_agents", []))
    cfg["custom_agents"] = [
        c for c in cfg.get("custom_agents", [])
        if c["name"].lower().replace(" ", "_") != agent_key
    ]
    if len(cfg["custom_agents"]) == original_len:
        raise HTTPException(status_code=404, detail=f"Custom agent '{agent_key}' not found")
    save_config(cfg)
    config_history.record("delete_custom_agent", before, cfg, target=agent_key)
    reload_agents()
    return {"ok": True, "agent": agent_key}
