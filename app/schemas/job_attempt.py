from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JobAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    attempt_number: int
    status: str
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None
