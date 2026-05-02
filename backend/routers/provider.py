"""Provider management endpoints."""

from fastapi import APIRouter, HTTPException

from deps import _provider_registry
from provider.adapters import create_openai_compat_provider

router = APIRouter()


@router.get("/api/providers")
async def list_providers():
    return {"providers": _provider_registry.list_providers()}


@router.post("/api/providers/{name}/test")
async def test_provider(name: str):
    provider = _provider_registry.get(name)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{name}' not found")
    try:
        ok = await provider.health_check()
    except Exception as e:
        return {"name": name, "ok": False, "error": str(e)}
    if not ok:
        return {
            "name": name,
            "ok": False,
            "error": "API returned an error — check base_url and API key. "
                     "Some providers do not support the /models endpoint.",
        }
    return {"name": name, "ok": ok}


@router.put("/api/providers/{name}")
async def update_provider(name: str, body: dict):
    _provider_registry.update_provider_config(name, body)
    return {"ok": True, "provider": name}


@router.post("/api/providers/custom")
async def add_custom_provider(body: dict):
    name = body.get("name")
    base_url = body.get("base_url")
    api_key = body.get("api_key")
    default_model = body.get("default_model")
    models = body.get("models", [])

    if not name or not base_url or not api_key:
        raise HTTPException(400, "name, base_url, api_key required")

    config = {
        "enabled": True,
        "base_url": base_url,
        "api_key": api_key,
        "default_model": default_model,
        "models": [{"id": m, "display_name": m} for m in models],
    }

    provider = create_openai_compat_provider(name, config)
    if provider:
        _provider_registry.register(provider)
        _provider_registry.update_provider_config(name, config)
    return {"ok": True, "provider": name}
