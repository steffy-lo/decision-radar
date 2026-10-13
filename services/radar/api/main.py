import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.radar.config import settings
from services.radar.api.routes import assessments, briefs, connections, decisions, health, impact, jobs, projects, reviews, sources

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
app.include_router(projects.router, prefix="/api/v1")
app.include_router(assessments.router, prefix="/api/v1")
app.include_router(decisions.router, prefix="/api/v1")
app.include_router(connections.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(sources.router, prefix="/api/v1")
app.include_router(impact.router, prefix="/api/v1")
app.include_router(reviews.router, prefix="/api/v1")
app.include_router(briefs.router, prefix="/api/v1")


@app.middleware("http")
async def prevent_private_api_caching(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/v1/") and request.url.path != "/api/v1/health":
        response.headers["Cache-Control"] = "private, no-store"
    return response


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
