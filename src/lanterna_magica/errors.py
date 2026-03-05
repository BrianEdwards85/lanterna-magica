class AppError(Exception):
    """Base error with a machine-readable code for GraphQL extensions."""

    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    code = "NOT_FOUND"


class ValidationError(AppError):
    code = "VALIDATION_ERROR"
