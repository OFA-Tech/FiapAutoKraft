class ApplicationError(Exception):
    """Base error for known application failures."""


class InfrastructureError(ApplicationError):
    """Raised when an infrastructure adapter fails."""


class DeviceBusyError(ApplicationError):
    """Raised when a device is busy with another command."""
