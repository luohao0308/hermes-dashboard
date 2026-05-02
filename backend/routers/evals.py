"""Eval and Config Version API — v1.4.

Endpoints:
    GET  /api/evals/summary              — aggregated eval metrics
    GET  /api/evals/results              — paginated eval results
    POST /api/evals/run                  — run offline eval and persist
    GET  /api/config-versions            — list config versions
    POST /api/config-versions            — create config version
    POST /api/config-versions/compare    — compare two config versions
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from database import get_db
from models import EvalResult, Runtime, ConfigVersion, Approval
from security.audit import write_audit_log
from security.rbac import require_role
from schemas.eval import (
    EvalResultResponse,
    EvalResultListResponse,
    EvalTrendPoint,
    EvalRuntimeBreakdown,
    EvalConfigBreakdown,
    EvalSummaryResponse,
    EvalRunRequest,
    EvalSampleResult,
    EvalRunResponse,
    ConfigVersionResponse,
    ConfigVersionListResponse,
    ConfigVersionCreate,
    ConfigCompareRequest,
    ConfigFieldChange,
    ConfigCompareResponse,
)

router = APIRouter(tags=["evals"])
limiter = Limiter(key_func=get_remote_address)


# ---------------------------------------------------------------------------
# GET /api/evals/summary
# ---------------------------------------------------------------------------


@router.get("/api/evals/summary", response_model=EvalSummaryResponse)
def get_eval_summary(
    runtime_id: Optional[uuid.UUID] = None,
    config_version: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(EvalResult)
    if runtime_id is not None:
        query = query.filter(EvalResult.runtime_id == runtime_id)
    if config_version:
        query = query.filter(EvalResult.config_version == config_version)
    if from_date:
        query = query.filter(EvalResult.created_at >= from_date)
    if to_date:
        query = query.filter(EvalResult.created_at <= to_date)

    rows = query.all()
    if not rows:
        return EvalSummaryResponse()

    total = len(rows)
    passed = sum(1 for r in rows if r.success)
    failed = total - passed
    scores = [float(r.score) for r in rows if r.score is not None]
    latencies = [r.latency_ms for r in rows if r.latency_ms is not None]
    costs = [float(r.cost) for r in rows if r.cost is not None]

    tool_errors = _avg_metric(rows, "tool_error_rate")
    handoffs = _sum_metric(rows, "handoff_count")
    approvals = _sum_metric(rows, "approval_count")

    by_runtime = _breakdown_by_runtime(db, rows)
    by_config = _breakdown_by_config(rows)
    trend = _compute_trend(rows)

    return EvalSummaryResponse(
        total=total,
        passed=passed,
        failed=failed,
        avg_score=round(sum(scores) / len(scores), 4) if scores else None,
        avg_latency_ms=round(sum(latencies) / len(latencies), 1) if latencies else None,
        avg_cost=round(sum(costs) / len(costs), 6) if costs else None,
        tool_error_rate=round(tool_errors, 4) if tool_errors is not None else None,
        handoff_count=handoffs,
        approval_count=approvals,
        by_runtime=by_runtime,
        by_config_version=by_config,
        trend=trend,
    )


def _avg_metric(rows: list, key: str) -> Optional[float]:
    values = [
        float(r.metrics_json[key])
        for r in rows
        if r.metrics_json and r.metrics_json.get(key) is not None
    ]
    return sum(values) / len(values) if values else None


def _sum_metric(rows: list, key: str) -> Optional[int]:
    values = [
        int(r.metrics_json[key])
        for r in rows
        if r.metrics_json and r.metrics_json.get(key) is not None
    ]
    return sum(values) if values else None


def _breakdown_by_runtime(db: Session, rows: list) -> list[EvalRuntimeBreakdown]:
    runtime_ids = list({r.runtime_id for r in rows})
    runtime_names = {}
    if runtime_ids:
        runtimes = db.query(Runtime).filter(Runtime.id.in_(runtime_ids)).all()
        runtime_names = {str(rt.id): rt.name for rt in runtimes}

    groups: dict[str, list] = {}
    for r in rows:
        key = str(r.runtime_id)
        groups.setdefault(key, []).append(r)

    result = []
    for rt_id, group in groups.items():
        scores = [float(r.score) for r in group if r.score is not None]
        result.append(EvalRuntimeBreakdown(
            runtime_id=rt_id,
            runtime_name=runtime_names.get(rt_id, rt_id[:8]),
            total=len(group),
            passed=sum(1 for r in group if r.success),
            failed=sum(1 for r in group if not r.success),
            avg_score=round(sum(scores) / len(scores), 4) if scores else None,
        ))
    return result


def _breakdown_by_config(rows: list) -> list[EvalConfigBreakdown]:
    groups: dict[str, list] = {}
    for r in rows:
        key = r.config_version or "(none)"
        groups.setdefault(key, []).append(r)

    result = []
    for cv, group in groups.items():
        scores = [float(r.score) for r in group if r.score is not None]
        result.append(EvalConfigBreakdown(
            config_version=cv,
            total=len(group),
            passed=sum(1 for r in group if r.success),
            failed=sum(1 for r in group if not r.success),
            avg_score=round(sum(scores) / len(scores), 4) if scores else None,
        ))
    return result


def _compute_trend(rows: list) -> list[EvalTrendPoint]:
    groups: dict[str, list] = {}
    for r in rows:
        day = r.created_at.strftime("%Y-%m-%d") if r.created_at else "unknown"
        groups.setdefault(day, []).append(r)

    result = []
    for day in sorted(groups.keys()):
        group = groups[day]
        scores = [float(r.score) for r in group if r.score is not None]
        latencies = [r.latency_ms for r in group if r.latency_ms is not None]
        costs = [float(r.cost) for r in group if r.cost is not None]
        tool_errors = [
            float(r.metrics_json["tool_error_rate"])
            for r in group
            if r.metrics_json and r.metrics_json.get("tool_error_rate") is not None
        ]
        handoffs = [
            int(r.metrics_json["handoff_count"])
            for r in group
            if r.metrics_json and r.metrics_json.get("handoff_count") is not None
        ]
        approvals = [
            int(r.metrics_json["approval_count"])
            for r in group
            if r.metrics_json and r.metrics_json.get("approval_count") is not None
        ]

        result.append(EvalTrendPoint(
            date=day,
            runs=len(group),
            passed=sum(1 for r in group if r.success),
            failed=sum(1 for r in group if not r.success),
            avg_score=round(sum(scores) / len(scores), 4) if scores else None,
            avg_latency_ms=round(sum(latencies) / len(latencies), 1) if latencies else None,
            avg_cost=round(sum(costs) / len(costs), 6) if costs else None,
            tool_error_rate=round(sum(tool_errors) / len(tool_errors), 4) if tool_errors else None,
            handoff_count=sum(handoffs) if handoffs else None,
            approval_count=sum(approvals) if approvals else None,
        ))
    return result


# ---------------------------------------------------------------------------
# GET /api/evals/results
# ---------------------------------------------------------------------------


@router.get("/api/evals/results", response_model=EvalResultListResponse)
def list_eval_results(
    runtime_id: Optional[uuid.UUID] = None,
    config_version: Optional[str] = None,
    sample_name: Optional[str] = None,
    success: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(EvalResult)
    if runtime_id is not None:
        query = query.filter(EvalResult.runtime_id == runtime_id)
    if config_version:
        query = query.filter(EvalResult.config_version == config_version)
    if sample_name:
        query = query.filter(EvalResult.sample_name == sample_name)
    if success is not None:
        query = query.filter(EvalResult.success == success)

    total = query.count()
    items = (
        query.order_by(EvalResult.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return EvalResultListResponse(
        items=[EvalResultResponse.model_validate(r) for r in items],
        total=total,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# POST /api/evals/run
# ---------------------------------------------------------------------------


@router.post("/api/evals/run", response_model=EvalRunResponse)
@limiter.limit("10/minute")
def run_eval(
    request: Request,
    body: EvalRunRequest,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("operator")),
):
    from agent.eval_runner import run_eval_samples

    runtime = db.get(Runtime, body.runtime_id)
    if not runtime:
        raise HTTPException(status_code=404, detail="Runtime not found")

    result = run_eval_samples(category=body.category)
    eval_run_id = result["eval_run_id"]

    for sample in result["results"]:
        eval_row = EvalResult(
            id=uuid.uuid4(),
            runtime_id=body.runtime_id,
            config_version=body.config_version,
            sample_name=sample.get("sample_id") or sample.get("title"),
            success=sample["passed"],
            score=sample["score"],
            metrics_json={
                "tool_error_rate": 1.0 if not sample["passed"] else 0.0,
                "handoff_count": 0,
                "approval_count": 0,
                "failure_category": sample.get("category"),
                "findings": sample.get("findings", []),
            },
        )
        db.add(eval_row)

    write_audit_log(
        db,
        actor_type="user",
        actor_id="api",
        action="eval.run",
        resource_type="eval_result",
        resource_id=eval_run_id,
        after_json={
            "runtime_id": str(body.runtime_id),
            "config_version": body.config_version,
            "count": result["count"],
            "passed": result["passed"],
            "failed": result["failed"],
            "avg_score": result["avg_score"],
        },
    )

    db.commit()

    return EvalRunResponse(
        eval_run_id=eval_run_id,
        mode=result["mode"],
        count=result["count"],
        passed=result["passed"],
        failed=result["failed"],
        avg_score=result["avg_score"],
        results=[
            EvalSampleResult(
                sample_id=s.get("sample_id"),
                category=s.get("category"),
                title=s.get("title"),
                score=s["score"],
                passed=s["passed"],
                findings=s.get("findings", []),
            )
            for s in result["results"]
        ],
    )


# ---------------------------------------------------------------------------
# GET /api/config-versions
# ---------------------------------------------------------------------------


@router.get("/api/config-versions", response_model=ConfigVersionListResponse)
def list_config_versions(
    runtime_id: Optional[uuid.UUID] = None,
    config_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(ConfigVersion)
    if runtime_id is not None:
        query = query.filter(ConfigVersion.runtime_id == runtime_id)
    if config_type:
        query = query.filter(ConfigVersion.config_type == config_type)

    total = query.count()
    items = (
        query.order_by(ConfigVersion.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return ConfigVersionListResponse(
        items=[ConfigVersionResponse.model_validate(c) for c in items],
        total=total,
    )


# ---------------------------------------------------------------------------
# POST /api/config-versions
# ---------------------------------------------------------------------------


@router.post("/api/config-versions", response_model=ConfigVersionResponse)
def create_config_version(
    body: ConfigVersionCreate,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("operator")),
):
    runtime = db.get(Runtime, body.runtime_id)
    if not runtime:
        raise HTTPException(status_code=404, detail="Runtime not found")

    # Guardrail: if this version scores higher than the current best,
    # force requires_approval=True to prevent unsupervised config changes.
    requires_approval = body.requires_approval
    if body.config_json and not requires_approval:
        current_best = (
            db.query(ConfigVersion)
            .filter(
                ConfigVersion.runtime_id == body.runtime_id,
                ConfigVersion.config_type == body.config_type,
            )
            .order_by(ConfigVersion.evaluation_score.desc().nullslast())
            .first()
        )
        if current_best and current_best.evaluation_score is not None:
            # If new version has a score, check if it's an improvement
            new_score = body.config_json.get("evaluation_score")
            if new_score is not None and float(new_score) > float(current_best.evaluation_score):
                requires_approval = True

    cv = ConfigVersion(
        id=uuid.uuid4(),
        runtime_id=body.runtime_id,
        config_type=body.config_type,
        version=body.version,
        config_json=body.config_json,
        requires_approval=requires_approval,
        created_by=body.created_by,
    )
    db.add(cv)
    db.flush()

    write_audit_log(
        db,
        actor_type="user",
        actor_id=body.created_by or "api",
        action="config_version.created",
        resource_type="config_version",
        resource_id=str(cv.id),
        after_json={
            "runtime_id": str(body.runtime_id),
            "config_type": body.config_type,
            "version": body.version,
            "requires_approval": requires_approval,
        },
    )

    if requires_approval:
        approval = Approval(
            id=uuid.uuid4(),
            run_id=None,
            status="pending",
            reason=f"Config version {body.version} requires approval",
            requested_by=body.created_by or "system",
        )
        db.add(approval)

    db.commit()
    db.refresh(cv)
    return ConfigVersionResponse.model_validate(cv)


# ---------------------------------------------------------------------------
# POST /api/config-versions/compare
# ---------------------------------------------------------------------------


@router.post("/api/config-versions/compare", response_model=ConfigCompareResponse)
def compare_config_versions(body: ConfigCompareRequest, db: Session = Depends(get_db)):
    before = db.get(ConfigVersion, body.before_version_id)
    if not before:
        raise HTTPException(status_code=404, detail="Before version not found")
    after = db.get(ConfigVersion, body.after_version_id)
    if not after:
        raise HTTPException(status_code=404, detail="After version not found")

    changes = _diff_configs(before.config_json or {}, after.config_json or {})
    score_delta = None
    if before.evaluation_score is not None and after.evaluation_score is not None:
        score_delta = round(float(after.evaluation_score) - float(before.evaluation_score), 4)

    # Determine if "after" is a recommended improvement
    recommended = (
        after.requires_approval
        and score_delta is not None
        and score_delta > 0
    )

    return ConfigCompareResponse(
        before=ConfigVersionResponse.model_validate(before),
        after=ConfigVersionResponse.model_validate(after),
        score_delta=score_delta,
        changes=changes,
        requires_approval=after.requires_approval,
        recommended=recommended,
    )


def _diff_configs(before: dict[str, Any], after: dict[str, Any]) -> list[ConfigFieldChange]:
    all_keys = sorted(set(before.keys()) | set(after.keys()))
    changes = []
    for key in all_keys:
        b = before.get(key)
        a = after.get(key)
        if b != a:
            changes.append(ConfigFieldChange(field=key, before=b, after=a))
    return changes


# ---------------------------------------------------------------------------
# POST /api/config-versions/{id}/apply — apply a config version
# ---------------------------------------------------------------------------


@router.post("/api/config-versions/{cv_id}/apply")
def apply_config_version(
    cv_id: uuid.UUID,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("operator")),
):
    """Apply a config version. Blocked if requires_approval is True and no
    approved approval record exists."""
    cv = db.get(ConfigVersion, cv_id)
    if not cv:
        raise HTTPException(status_code=404, detail="Config version not found")

    if cv.requires_approval:
        # Check if there's an approved approval for this config version
        approval = (
            db.query(Approval)
            .filter(
                Approval.reason.ilike(f"%{str(cv_id)}%"),
                Approval.status == "approved",
            )
            .first()
        )
        if not approval:
            raise HTTPException(
                status_code=403,
                detail="Config version requires approval before it can be applied. "
                       "Submit an approval request and get it approved first.",
            )

    # Mark as the active version by updating the runtime's config
    runtime = db.get(Runtime, cv.runtime_id)
    if runtime:
        runtime.config_json = {**(runtime.config_json or {}), **(cv.config_json or {})}

    write_audit_log(
        db,
        actor_type="user",
        actor_id="api",
        action="config_version.applied",
        resource_type="config_version",
        resource_id=str(cv_id),
        after_json={
            "runtime_id": str(cv.runtime_id),
            "config_type": cv.config_type,
            "version": cv.version,
        },
    )
    db.commit()
    return {"status": "applied", "config_version_id": str(cv_id)}
