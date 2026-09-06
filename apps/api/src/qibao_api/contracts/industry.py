"""Canonical industry taxonomy contracts.

申万行业是平台唯一正式行业口径。其它供应商分类只能作为原始证据保存。
"""

from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


IndustryLevel = Literal["一级", "二级", "三级"]


class ShenwanIndustry(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str = Field(pattern=r"^SW[0-9]{6}$")
    name: str = Field(min_length=1, max_length=80)
    level: IndustryLevel
    version: str = Field(min_length=1, max_length=32)


class IndustryMappingEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_system: str = Field(min_length=1)
    source_code: str | None = None
    source_name: str | None = None
    matched_by: Literal["exact_code", "exact_name", "alias", "manual", "unmapped"]
    observed_at: AwareDatetime
    evidence_ref: str | None = None


class CanonicalIndustryAssignment(BaseModel):
    model_config = ConfigDict(frozen=True)

    industry: ShenwanIndustry | None = None
    evidence: IndustryMappingEvidence

    @property
    def is_verified(self) -> bool:
        return self.industry is not None and self.evidence.matched_by != "unmapped"
