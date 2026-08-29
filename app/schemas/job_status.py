from pydantic import BaseModel


class JobStatusResponse(BaseModel):
    id: int
    status: str
