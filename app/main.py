from contextlib import asynccontextmanager
from fastapi import FastAPI
from .database import Base, engine
from .routers import auth, cart, orders, products


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="E-commerce API", version="1.0.0", lifespan=lifespan)
for r in (auth.router, products.router, cart.router, orders.router):
    app.include_router(r)


@app.get("/", tags=["Health"])
def health():
    return {"status": "ok", "docs": "/docs"}