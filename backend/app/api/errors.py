"""
API error handlers.

FastAPI's standard 422 answer repeats the submitted value of every refused field. For a sign-in
or a password change that value is a password, so the values are left out of the answer: the
location and the message are what a client needs.
"""

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """The standard 422 body without the submitted values."""

    assert isinstance(exc, RequestValidationError)
    errors = [
        {key: value for key, value in error.items() if key != "input"} for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(errors)})


__all__ = ["validation_error_handler"]
