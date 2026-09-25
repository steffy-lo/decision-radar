import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.radar.config import settings
from services.radar.api.routes import health

app = FastAPI(
    title="Decision Radar API",
    version="0.1.0",
    description="Core API backend for Decision Radar organisational memory and decision intelligence.",
)

# CORS Middleware
origins = [
    settings.WEB_ORIGIN,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
# Root health route
app.include_router(health.router, tags=["Health"])

# Prefix route for proxy matching /api/v1
app.include_router(health.router, prefix="/api/v1", tags=["Health"])


@app.get("/")
def root():
    return {
        "name": "Decision Radar API",
        "status": "online",
        "docs_url": "/docs",
    }


if __name__ == "__main__":
    uvicorn.run(
        "services.radar.api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )
