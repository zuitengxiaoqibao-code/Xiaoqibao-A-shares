from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)


NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
SnapshotHash = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
CandidateSentimentQuality = Literal["ready", "partial", "unavailable"]
CandidateSentimentFreshness = Literal["current", "stale"]
CandidateSentimentBand = Literal[
    "strongly_bearish",
    "cautious",
    "neutral",
    "positive",
    "overheated",
    "unavailable",
]
CandidateSentimentComponentName = Literal["news", "hotspot", "fund_flow"]


class CandidateSentimentComponent(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: CandidateSentimentComponentName
    status: Literal["ready", "unavailable"]
    score: Decimal | None = Field(default=None, ge=0, le=100)
    weight: Decimal = Field(gt=0, le=100)
    summary: NonBlank
    observed_at: AwareDatetime | None = None
    evidence_ids: tuple[NonBlank, ...] = ()

    @model_validator(mode="after")
    def validate_score_state(self) -> "CandidateSentimentComponent":
        if (self.status == "unavailable") != (self.score is None):
            raise ValueError("unavailable component and missing score must agree")
        if self.status == "ready" and self.observed_at is None:
            raise ValueError("ready component requires observation time")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("component evidence ids must be unique")
        return self


class CandidateSentimentSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: NonBlank | None = None
    candidate_snapshot_id: NonBlank
    candidate_input_hash: SnapshotHash
    symbol: str = Field(pattern=r"^\d{6}$")
    quality: CandidateSentimentQuality
    freshness: CandidateSentimentFreshness
    score: Decimal | None = Field(default=None, ge=0, le=100)
    band: CandidateSentimentBand
    coverage_percent: Decimal = Field(ge=0, le=100)
    components: tuple[CandidateSentimentComponent, ...]
    primary_reason: NonBlank
    primary_risk: NonBlank
    beginner_guidance: NonBlank
    observed_at: AwareDatetime
    generated_at: AwareDatetime
    source_snapshot_ids: tuple[NonBlank, ...]
    formula_version: Literal["candidate-sentiment-v1"] = "candidate-sentiment-v1"

    @model_validator(mode="after")
    def validate_snapshot(self) -> "CandidateSentimentSnapshot":
        unavailable = self.score is None
        if unavailable != (self.band == "unavailable"):
            raise ValueError("missing score and unavailable band must agree")
        if unavailable != (self.quality == "unavailable"):
            raise ValueError("missing score and unavailable quality must agree")
        if self.quality == "ready" and self.coverage_percent != Decimal("100"):
            raise ValueError("ready sentiment requires complete coverage")
        if self.quality == "partial" and not Decimal("60") <= self.coverage_percent < Decimal("100"):
            raise ValueError("partial sentiment requires 60-99 percent coverage")
        if self.quality == "unavailable" and self.coverage_percent >= Decimal("60"):
            raise ValueError("unavailable sentiment requires coverage below 60 percent")
        expected = {"news", "hotspot", "fund_flow"}
        names = [component.name for component in self.components]
        if len(names) != 3 or set(names) != expected:
            raise ValueError("sentiment requires three unique fixed components")
        if sum((component.weight for component in self.components), Decimal("0")) != Decimal("100"):
            raise ValueError("sentiment component weights must total 100")
        if self.observed_at > self.generated_at:
            raise ValueError("sentiment observation cannot follow generation")
        if len(set(self.source_snapshot_ids)) != len(self.source_snapshot_ids):
            raise ValueError("source snapshot ids must be unique")
        return self


class CandidateSentimentBatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: NonBlank | None = None
    candidate_snapshot_id: NonBlank
    candidate_input_hash: SnapshotHash
    as_of: date
    cutoff: AwareDatetime
    quality: CandidateSentimentQuality
    items: tuple[CandidateSentimentSnapshot, ...] = Field(max_length=20)
    generated_at: AwareDatetime

    @model_validator(mode="after")
    def validate_batch(self) -> "CandidateSentimentBatch":
        symbols = [item.symbol for item in self.items]
        if len(symbols) != len(set(symbols)):
            raise ValueError("candidate sentiment symbols must be unique")
        if any(item.candidate_snapshot_id != self.candidate_snapshot_id for item in self.items):
            raise ValueError("item candidate snapshot differs from batch")
        if any(item.candidate_input_hash != self.candidate_input_hash for item in self.items):
            raise ValueError("item candidate input hash differs from batch")
        if any(item.generated_at > self.generated_at for item in self.items):
            raise ValueError("item generation cannot follow batch generation")
        expected_quality: CandidateSentimentQuality = (
            "ready" if self.items and all(item.quality == "ready" for item in self.items)
            else "partial" if any(item.score is not None for item in self.items)
            else "unavailable"
        )
        if self.quality != expected_quality:
            raise ValueError("batch quality does not match item quality")
        return self
