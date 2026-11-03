from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, HttpUrl


class MilestoneSubmissionSchema(BaseModel):
    freelancer_id: str = Field(..., min_length=1)
    deployment_url: Optional[HttpUrl] = None
    repository: Optional[str] = Field(None, description="GitHub owner/repository, e.g. org/project")
    evidence_url: Optional[HttpUrl] = None
    files: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Optional file evidence keyed by relative path")
