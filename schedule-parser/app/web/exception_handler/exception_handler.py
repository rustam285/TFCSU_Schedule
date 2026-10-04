from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.requests import Request
from fastapi.responses import JSONResponse


def register_exception_handlers(app: FastAPI, logger):
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = None
        try:
            errors = {
                error["loc"][-1]: error["msg"]
                for error in exc.errors()
            }
        except Exception:
            errors = exc.errors()
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation Error",
                "details": errors
            },
        )

    @app.exception_handler(HTTPException)
    async def custom_http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"message": f"{exc.detail}"},
        )

    @app.exception_handler(Exception)
    async def internal_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "Something went wrong. Try again later",
            },
        )
