from __future__ import annotations

from datetime import datetime, timedelta, timezone

from qibao_api.contracts.news import NormalizedNewsEvent


class NewsRetentionPolicy:
    """Return auditable expiry times without deleting original evidence."""

    def expiry_for(self, event: NormalizedNewsEvent) -> datetime:
        if event.event_type in {"intraday_alert", "market_anomaly", "hotspot"}:
            days = 3
        elif any(marker in event.headline for marker in ("业绩", "财报", "问询", "监管", "处罚", "公告")):
            days = 3650
        elif any(marker in event.headline for marker in ("政策", "规划", "改革", "发布会")):
            days = 730
        else:
            days = 30
        occurred = event.occurred_at
        if occurred.tzinfo is None or occurred.utcoffset() is None:
            occurred = occurred.replace(tzinfo=timezone.utc)
        return occurred.astimezone(timezone.utc) + timedelta(days=days)
