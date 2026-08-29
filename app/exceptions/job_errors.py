class JobError(Exception):
    """Base job error."""


class JobNotFoundError(JobError):
    """Raised when a requested job does not exist."""
