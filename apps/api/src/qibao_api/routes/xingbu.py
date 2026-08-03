from fastapi import APIRouter, Request

from qibao_api.xingbu.status import build_risk_status
router = APIRouter(prefix="/api/v1/xingbu", tags=["刑部"])
RULE_VERSION = "research-risk-v2"


@router.get("/status")
def status(request: Request):
    return build_risk_status(
        sentiment_repository=getattr(request.app.state, "market_sentiment_repository", None),
        news_repository=getattr(request.app.state, "news_repository", None),
    )
