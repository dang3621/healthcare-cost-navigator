from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.providers import router as providers_router
from app.api.assistant import router as assistant_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Healthcare Cost Navigator starting up...")
    yield
    # Shutdown
    print("👋 Healthcare Cost Navigator shutting down...")


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(providers_router)
app.include_router(assistant_router)


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Healthcare Cost Navigator API",
        "version": settings.api_version,
        "description": "Search hospitals by MS-DRG procedures with AI assistant",
        "endpoints": {
            "providers": "/providers - Search hospitals by DRG, ZIP code, and radius",
            "ask": "/ask - Natural language interface for healthcare queries",
            "docs": "/docs - Interactive API documentation",
            "examples": "/ask/examples - Example questions for the AI assistant"
        },
        "sample_queries": [
            "GET /providers?drg=470&zip_code=10001&radius_km=40",
            "POST /ask with body: {'question': 'Who is cheapest for knee replacement near 10001?'}"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "healthcare-cost-navigator"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
