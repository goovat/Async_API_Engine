from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.authentication import get_current_user
from app.api.dependencies.database import get_db
from app.exceptions.job_errors import JobNotFoundError
from app.models.user import User
from app.schemas.job_attempt import JobAttemptResponse
from app.schemas.job_create import JobCreateRequest
from app.schemas.job_response import JobResponse
from app.schemas.job_status import JobStatusResponse
from app.services.job_attempt_service import JobAttemptService
from app.services.job_service import JobService
from app.services.job_status_service import JobStatusService
from app.services.retry_service import RetryService
from app.workers.queue import JobQueue

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_job(
    payload: JobCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="X-Idempotency-Key")] = None,
):
    queue = JobQueue()
    service = JobService(session, queue=queue)

    job = await service.create_job(
        user_id=current_user.id,
        job_type=payload.job_type,
        payload=payload.payload,
        idempotency_key=idempotency_key,
    )

    await session.commit()

    return job


@router.get(
    "/{job_id}",
    response_model=JobResponse,
)
async def get_job(
    job_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = JobService(session)

    job = await service.get_job(
        job_id=job_id,
        user_id=current_user.id,
    )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return job


@router.get(
    "/{job_id}/status",
    response_model=JobStatusResponse,
)
async def get_job_status(
    job_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = JobStatusService(session)

    job = await service.get_status(
        job_id=job_id,
        user_id=current_user.id,
    )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return job

@router.get(
    "/{job_id}/attempts",
    response_model=list[JobAttemptResponse],
)
async def get_job_attempts(
    job_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = JobAttemptService(session)

    try:
        attempts = await service.get_attempts(
            job_id=job_id,
            user_id=current_user.id,
        )
    except JobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return attempts


@router.post(
    "/{job_id}/retry",
    response_model=JobResponse,
)
async def retry_job(
    job_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = RetryService(session)

    try:
        job = await service.retry_job(
            job_id=job_id,
            user_id=current_user.id,
        )
    except JobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    await session.commit()

    return job
