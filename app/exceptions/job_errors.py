class JobError(Exception):
    """Base job error."""


class JobNotFoundError(JobError):
    """Raised when a requested job does not exist."""


class JobRetryError(JobError):
    """Base error for job retry failures."""


class JobNotRetryableError(JobRetryError):
    """Raised when a job is not in a retryable state."""


class MaxRetryAttemptsError(JobRetryError):
    """Raised when a job has reached the maximum retry attempts."""
