from pydantic import BaseModel, ConfigDict

from qibao_api.contracts.company_research import CompanyResearchAIResult
from qibao_api.contracts.task_progress import TaskProgress


class CompanyResearchAITaskSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    progress: TaskProgress
    result: CompanyResearchAIResult | None = None
