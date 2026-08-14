from pydantic import BaseModel, ConfigDict

from qibao_api.contracts.company_research import CompanyResearchResponse
from qibao_api.contracts.task_progress import TaskProgress


class CompanyResearchTaskSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    progress: TaskProgress
    result: CompanyResearchResponse | None = None

