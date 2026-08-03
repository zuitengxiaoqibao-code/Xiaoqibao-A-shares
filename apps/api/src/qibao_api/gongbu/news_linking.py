from collections.abc import Callable, Mapping
from decimal import Decimal
import re

from qibao_api.contracts.instruments import (
    validate_a_share_code,
    validate_convertible_bond_code,
)
from qibao_api.contracts.market import AssetKind
from qibao_api.contracts.news import (
    EvidenceCitation,
    NewsArticle,
    NormalizedNewsEvent,
)


class DeterministicNewsLinker:
    def __init__(
        self,
        *,
        instrument_aliases: Mapping[tuple[AssetKind, str], tuple[str, ...]]
        | Callable[[], Mapping[tuple[AssetKind, str], tuple[str, ...]]],
        industry_keywords: Mapping[str, tuple[str, ...]],
        theme_keywords: Mapping[str, tuple[str, ...]],
    ) -> None:
        self.instrument_aliases = instrument_aliases
        self.industry_keywords = industry_keywords
        self.theme_keywords = theme_keywords

    def link(
        self,
        article: NewsArticle,
        *,
        context_instruments: tuple[tuple[AssetKind, str], ...] = (),
    ) -> NormalizedNewsEvent:
        text = f"{article.title}\n{article.summary or ''}"
        alias_map = self.instrument_aliases() if callable(self.instrument_aliases) else self.instrument_aliases
        alias_matches = tuple(
            (instrument, alias)
            for instrument, aliases in alias_map.items()
            for alias in aliases
            if alias in text
        )
        configured = tuple(dict.fromkeys(instrument for instrument, _ in alias_matches))
        code_matches = tuple(dict.fromkeys(re.findall(r"(?<!\d)\d{6}(?!\d)", text)))
        explicit = tuple(
            instrument
            for code in code_matches
            if (instrument := _recognized_instrument(code)) is not None
        )
        explicit_instruments = tuple(dict.fromkeys((*configured, *explicit)))
        context = self._validate_context(context_instruments)
        instruments = tuple(dict.fromkeys((*explicit_instruments, *context)))
        industries = tuple(
            name
            for name, keywords in self.industry_keywords.items()
            if any(keyword in text for keyword in keywords)
        )
        themes = tuple(
            name
            for name, keywords in self.theme_keywords.items()
            if any(keyword in text for keyword in keywords)
        )
        has_taxonomy = bool(industries or themes)
        if explicit_instruments:
            association_kind = "direct"
            confidence = Decimal("1")
            reasons = tuple(dict.fromkeys(
                tuple(f"company_alias:{alias}" for _, alias in alias_matches)
                + tuple(f"security_code:{code}" for code in code_matches if _recognized_instrument(code))
            ))
        elif context:
            association_kind = "context"
            confidence = Decimal("0.85")
            reasons = tuple(f"source_context:{symbol}" for _, symbol in context)
        elif has_taxonomy:
            association_kind = "theme"
            confidence = Decimal("0.60")
            reasons = tuple(
                [f"industry_keyword:{name}" for name in industries]
                + [f"theme_keyword:{name}" for name in themes]
            )
        else:
            association_kind = "macro"
            confidence = Decimal("0")
            reasons = ()
        review_state = (
            "verified"
            if article.source_verified and confidence >= Decimal("0.80")
            else "pending"
        )
        citation = EvidenceCitation(
            citation_id=f"citation-{article.article_id}",
            article_id=article.article_id,
            canonical_url=article.canonical_url,
            publisher=article.publisher,
            published_at=article.published_at,
            quoted_text=article.title,
            content_hash=article.content_hash,
        )
        return NormalizedNewsEvent(
            event_id=f"event-{article.article_id}",
            event_type="market_news",
            headline=article.title,
            occurred_at=article.published_at,
            normalized_at=article.fetched_at,
            affected_instruments=instruments,
            industries=industries,
            themes=themes,
            citations=(citation,),
            association_confidence=confidence,
            association_kind=association_kind,
            association_reasons=reasons,
            review_state=review_state,
        )

    @staticmethod
    def _validate_context(
        values: tuple[tuple[AssetKind, str], ...],
    ) -> tuple[tuple[AssetKind, str], ...]:
        if len(values) > 1:
            raise ValueError("news context must contain at most one instrument")
        for asset, symbol in values:
            if asset is not AssetKind.A_SHARE:
                raise ValueError("news context only accepts an A-share symbol")
            validate_a_share_code(symbol)
        if len(set(values)) != len(values):
            raise ValueError("news context instruments must be unique")
        return values


def _recognized_instrument(code: str) -> tuple[AssetKind, str] | None:
    try:
        return AssetKind.A_SHARE, validate_a_share_code(code)
    except ValueError:
        pass
    try:
        return AssetKind.CONVERTIBLE_BOND, validate_convertible_bond_code(code)
    except ValueError:
        return None
