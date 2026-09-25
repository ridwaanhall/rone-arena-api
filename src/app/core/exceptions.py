class AppError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: object = None,
        extra: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        self.extra = extra or {}


def validation_error(error_type: str, param: str, msg: str, value: object, ctx: dict) -> AppError:
    """422 shaped like FastAPI's own validation errors, for checks made after parsing."""
    return AppError(
        status_code=422,
        code="VALIDATION_ERROR",
        message="Validation failed.",
        details=[{"type": error_type, "loc": ["path", param], "msg": msg, "input": value, "ctx": ctx}],
        extra={"code": "VALIDATION_ERROR"},
    )
