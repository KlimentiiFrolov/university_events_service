from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from lifespan import Lifespan
from src.api import main_router
from src.core.config import settings
from src.core.logger import log


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_lifespan = Lifespan()

    await app_lifespan.startup()
    yield
    await app_lifespan.shutdown()


app = FastAPI(
    title="University Events API",
    lifespan=lifespan,
)

app.include_router(main_router)


@app.middleware("http")
async def catch_unhandled_exceptions(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:  # noqa: BLE001
        log.exception("Unhandled error: %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error. Please try again later."},
        )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.runtime.host,
        port=settings.runtime.port,
        reload=settings.runtime.reload,
    )
