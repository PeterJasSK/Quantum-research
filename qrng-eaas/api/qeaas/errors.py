"""AC-10, Q1: flat error envelope `{"error": "<slug>"}` for every error response,
matching the shape the low-entropy gate already returns."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(
        self, status_code: int, code: str, headers: dict[str, str] | None = None
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.headers = headers
        super().__init__(code)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content={"error": exc.code}, headers=exc.headers
        )

    @app.exception_handler(HTTPException)
    async def _http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and "error" in detail:
            content = detail
        else:
            content = {"error": str(detail)}
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(status_code=422, content={"error": "bad_request"})
