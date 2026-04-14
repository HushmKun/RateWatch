from __future__ import annotations

from dataclasses import dataclass

from fastapi.responses import JSONResponse


@dataclass(frozen=True)
class ErrorTemplate:
    code: str
    message: str
    status_code: int

    def with_message(self, message: str) -> "ErrorTemplate":
        return ErrorTemplate(code=self.code, message=message, status_code=self.status_code)


class RateWatchError(Exception):
    def __init__(self, error: ErrorTemplate):
        super().__init__(error.message)
        self.error = error


PAIR_NOT_FOUND = ErrorTemplate(
    code="PAIR_NOT_FOUND",
    message="Currency pair is not tracked.",
    status_code=404,
)
RATE_UNAVAILABLE = ErrorTemplate(
    code="RATE_UNAVAILABLE",
    message="Rate is temporarily unavailable.",
    status_code=503,
)
INVALID_PAIR_FORMAT = ErrorTemplate(
    code="INVALID_PAIR_FORMAT",
    message="Currency pair must be in BASE/TARGET format.",
    status_code=422,
)
HISTORY_RANGE_TOO_LARGE = ErrorTemplate(
    code="HISTORY_RANGE_TOO_LARGE",
    message="Requested history range exceeds the allowed 90 days.",
    status_code=422,
)


def format_error_response(exc: RateWatchError | ErrorTemplate) -> JSONResponse:
    error = exc.error if isinstance(exc, RateWatchError) else exc
    return JSONResponse(
        status_code=error.status_code,
        content={
            "error": {
                "code": error.code,
                "message": error.message,
                "docs": "/docs",
            }
        },
    )
