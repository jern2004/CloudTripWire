from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database import init_db
from app.routers import health, metrics, incidents, evidence

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Multi-Cloud Honeytoken Security Monitoring System",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS - CRITICAL for frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(metrics.router)
app.include_router(incidents.router)
app.include_router(evidence.router)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    print("🚀 Starting CloudTripwire API...")
    init_db()
    print(f"✅ {settings.APP_NAME} v{settings.APP_VERSION} is running!")
    print(f"📚 API Documentation: http://localhost:8000/docs")
    print(f"🔗 Frontend should connect to: http://127.0.0.1:8000/api")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
