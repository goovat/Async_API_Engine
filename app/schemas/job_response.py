from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    job_type: str
    payload: str
    status: str
    created_at: datetime
    updated_at: datetime
