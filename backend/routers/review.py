"""Code review, GitHub PR, and webhook endpoints."""

from typing import Optional

from fastapi import APIRouter, Query, HTTPException, Request

from deps import _provider_registry, _review_store, _cost_tracker
from review.github_adapter import GitHubAdapter
from review.pipeline import ReviewPipeline
from review.consensus import ConsensusEngine

router = APIRouter()


@router.get("/api/github/prs")
async def list_github_prs(
    repo: str = Query(...),
    state: str = Query("open"),
    limit: int = Query(20, ge=1, le=100),
):
    github = GitHubAdapter()
    try:
        pulls = await github.list_pulls(repo=repo, state=state, limit=limit)
        return {
            "repo": repo,
            "pulls": [
                {
                    "number": pr["number"],
                    "title": pr["title"],
                    "author": pr["user"]["login"],
                    "state": pr["state"],
                    "created_at": pr["created_at"],
                    "updated_at": pr["updated_at"],
                    "html_url": pr["html_url"],
                    "draft": pr.get("draft", False),
                }
                for pr in pulls
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"GitHub API error: {e}")
    finally:
        await github.close()


@router.get("/api/reviews")
async def list_reviews(
    repo: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    reviews = _review_store.list_reviews(repo=repo, status=status, limit=limit, offset=offset)
    return {"reviews": [r.model_dump() for r in reviews], "total": len(reviews)}


@router.get("/api/reviews/stats")
async def get_review_stats():
    return _review_store.get_stats()


@router.get("/api/reviews/{review_id}")
async def get_review(review_id: str):
    review = _review_store.get(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review.model_dump()


@router.post("/api/reviews/trigger")
async def trigger_review(body: dict):
    repo = body.get("repo")
    pr_number = body.get("pr_number")
    if not repo or not pr_number:
        raise HTTPException(status_code=400, detail="repo and pr_number required")

    github = GitHubAdapter()
    consensus = ConsensusEngine(min_agreement=2)
    available = list(_provider_registry._providers.keys())
    models = body.get("models", available)
    pipeline = ReviewPipeline(
        _provider_registry, github, consensus,
        review_models=models, cost_tracker=_cost_tracker,
    )

    try:
        review = await pipeline.review_pr(repo, int(pr_number))
        _review_store.save(review)
        return review.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review failed: {e}")
    finally:
        await github.close()


@router.post("/api/webhooks/github")
async def github_webhook(request: Request):
    body = await request.json()
    action = body.get("action")
    pr = body.get("pull_request")

    if action not in ("opened", "synchronize") or not pr:
        return {"status": "ignored", "action": action}

    repo = body.get("repository", {}).get("full_name", "")
    pr_number = pr.get("number", 0)

    github = GitHubAdapter()
    consensus = ConsensusEngine(min_agreement=2)
    pipeline = ReviewPipeline(_provider_registry, github, consensus)

    try:
        review = await pipeline.review_pr(repo, pr_number)
        _review_store.save(review)
        return {"status": "completed", "review_id": review.id}
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        await github.close()
