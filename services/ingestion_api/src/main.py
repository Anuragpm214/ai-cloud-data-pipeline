from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes import router

app = FastAPI(
    title="AI-Powered Cloud Data Pipeline API",
    description="Scalable Cloud Data Ingestion, Transformation, and AI Inference Pipeline",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "ingestion-api"}
