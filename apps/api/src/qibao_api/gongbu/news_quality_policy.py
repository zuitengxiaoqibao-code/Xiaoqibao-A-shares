from __future__ import annotations

from dataclasses import dataclass
import re

from qibao_api.contracts.news import NewsArticle, NormalizedNewsEvent


_ADVERTISING_MARKERS = (
    "扫码",
    "开户链接",
    "优惠券",
    "免费领取",
    "加微信",
    "推广",
    "广告",
)


@dataclass(frozen=True)
class NewsQualityDecision:
    accepted: bool
    reason: str


class NewsQualityPolicy:
    """Apply conservative, evidence-backed quality gates before persistence."""

    def evaluate(
        self, article: NewsArticle, event: NormalizedNewsEvent
    ) -> NewsQualityDecision:
        text = f"{article.title}\n{article.summary or ''}".strip()
        if any(marker in text for marker in _ADVERTISING_MARKERS):
            return NewsQualityDecision(False, "advertising")
        if event.association_kind in {"direct", "context"} and event.affected_instruments:
            return NewsQualityDecision(True, "a_share_relevant")
        if len(re.sub(r"\s+", "", article.title)) < 6:
            return NewsQualityDecision(False, "unrelated_or_low_information")
        if event.affected_instruments or event.industries or event.themes:
            return NewsQualityDecision(True, "a_share_relevant")
        return NewsQualityDecision(False, "unrelated_or_low_information")
