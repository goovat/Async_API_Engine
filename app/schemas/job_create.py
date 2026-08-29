from pydantic import BaseModel, Field


class JobCreateRequest(BaseModel):
    job_type: str = Field(min_length=1, max_length=100)
    payload: str = Field(min_length=1)
