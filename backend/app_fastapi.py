import os
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from backend.azure_vision import analyze_image
from backend.azure_openai import generate_insights
from backend.physical_processing import evaluate_physical_scan
from backend.cognitive_processing import evaluate_cognitive_scan

load_dotenv()

# -------------------------
# App
# -------------------------
APP = FastAPI(title="LifeScan AI")

APP.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev-safe
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# Utils
# -------------------------
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp", "gif"}


def _is_allowed(filename: Optional[str]) -> bool:
    return filename and "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


async def _read_image(upload: UploadFile) -> bytes:
    if not _is_allowed(upload.filename):
        raise HTTPException(status_code=400, detail="Unsupported file type")
    data = await upload.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty image")
    return data


def _shape_response(mode: str, features: Dict[str, Any], scores: Dict[str, Any], explanation: str):
    return {
        "mode": mode,
        "summary": explanation,
        "healthScore": scores.get("healthScore") or scores.get("score"),
        "confidence": scores.get("confidence", 0.9),
        "highlights": scores.get("highlights", []),
        "recommendations": scores.get("recommendations", []),
        "features": features,
        "scores": scores,
    }


# -------------------------
# Health
# -------------------------
@APP.get("/api/health")
async def health():
    return {"status": "ok"}


# -------------------------
# Physical Scan
# -------------------------
@APP.post("/api/scan/physical")
async def physical_scan(image: UploadFile = File(...)):
    img = await _read_image(image)
    features = analyze_image(img)
    scores = evaluate_physical_scan(features)
    explanation = generate_insights(scores)
    return JSONResponse(_shape_response("physical", features, scores, explanation))


# -------------------------
# Cognitive Scan
# -------------------------
@APP.post("/api/scan/cognitive")
async def cognitive_scan(image: UploadFile = File(...)):
    img = await _read_image(image)
    features = analyze_image(img)
    scores = evaluate_cognitive_scan(features)
    explanation = generate_insights(scores)
    return JSONResponse(_shape_response("cognitive", features, scores, explanation))


# -------------------------
# Frontend Convenience Endpoint
# -------------------------
@APP.post("/scan")
async def scan(image: UploadFile = File(...), mode: str = "physical"):
    mode = mode.lower()
    if mode == "physical":
        return await physical_scan(image)
    return await cognitive_scan(image)


# -------------------------
# Run
# -------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app_fastapi:APP",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
