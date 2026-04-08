from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.database import init_db
from app.routers import gc, homeowner, messages


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Bathroom Remodel Estimator", lifespan=lifespan)
app.include_router(gc.router)
app.include_router(homeowner.router)
app.include_router(messages.router)


@app.get("/")
async def root():
    return RedirectResponse(url="/gc/login")
