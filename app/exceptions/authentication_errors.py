class AuthenticationError(Exception):
    """Base authentication error."""


class InvalidCredentialsError(AuthenticationError):
    """Raised when authentication credentials are invalid."""


class UserAlreadyExistsError(AuthenticationError):
    """Raised when attempting to register an existing user."""
