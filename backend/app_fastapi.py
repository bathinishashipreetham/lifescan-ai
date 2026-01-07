"""
FastAPI application for LifeScan AI.

This file:
- Serves the existing frontend static files (cognitive_scan.html / physical_scan.html / JS / CSS)
- Provides robust /api/scan/cognitive and /api/scan/physical endpoints (accept multipart/form-data)
- Adds a convenience POST /scan endpoint (defaulting to cognitive) for the existing frontend which posts to /scan
- Adds CORS and basic validation / error handling

Expectations:
- backend.azure_vision.analyze_image accepts raw image bytes and returns vision features
- backend.cognitive_processing.evaluate_cognitive_scan and backend.physical_processing.evaluate_physical_scan accept the vision features and return scores dicts
- backend.azure_openai.generate_insights accepts a dict or text and returns a string (explanation)
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv

# Import your business logic (these must be present in the backend package)
from backend.azure_vision import analyze_image
from backend.azure_openai import generate_insights
from backend.physical_processing import evaluate_physical_scan
from backend.cognitive_processing import evaluate_cognitive_scan

load_dotenv()

# Configuration
APP = FastAPI(title="LifeScan AI")
# Allow origins can be restricted in prod (set env var FRONTEND_ORIGINS comma-separated)
_frontend_origins = os.environ.get("FRONTEND_ORIGINS", "*")
if _frontend_origins == "*":
    allow_origins = ["*"]
else:
    allow_origins = [o.strip() for o in _frontend_origins.split(",") if o.strip()]

APP.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
BASE_DIR = Path(__file__).resolve().parents[1]  # repo root/backend/.. -> repo root
FRONTEND_DIR = BASE_DIR / "frontend"
if FRONTEND_DIR.exists():
    # Mount static files under /frontend (so references like styles.css still resolve)
    APP.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend_static")


# Utils
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp", "gif"}


def _is_allowed_filename(filename: Optional[str]) -> bool:
    if not filename:
        return False
    parts = filename.rsplit(".", 1)
    if len(parts) != 2:
        return False
    return parts[1].lower() in ALLOWED_EXTENSIONS


async def _read_upload_file(upload: UploadFile) -> bytes:
    if not _is_allowed_filename(upload.filename):
        raise HTTPException(status_code=400, detail="Unsupported file type")
    contents = await upload.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file uploaded")
    return contents


def _shape_response(mode: str, vision_features: Dict[str, Any], scores: Dict[str, Any], explanation: Any) -> Dict[str, Any]:
    """
    Normalize the response shape used by the frontend. The frontend expects
    fields such as summary/healthScore/highlights/recommendations/regions.
    We attempt to map available data into that shape while preserving raw
    features and scores for debugging.
    """
    # Attempt to extract reasonable fields from explanation (string) and scores (dict)
    summary = explanation if isinstance(explanation, str) else (explanation.get("summary") if isinstance(explanation, dict) else "")
    # Try common keys from scores
    health_score = scores.get("healthScore") or scores.get("health_score") or scores.get("score") or scores.get("health", None)
    cognitive_score = scores.get("cognitiveScore") or scores.get("cognitive_score") or scores.get("cognitive", None)

    # Provide defaults and rounding
    def _norm_score(v):
        try:
            return int(round(float(v)))
        except Exception:
            return None

    response = {
        "mode": mode,
        "summary": summary or "",
        "healthScore": _norm_score(health_score) if health_score is not None else None,
        "cognitiveScore": _norm_score(cognitive_score) if cognitive_score is not None else None,
        "confidence": scores.get("confidence") if isinstance(scores.get("confidence"), (int, float)) else None,
        "highlights": scores.get("highlights") or scores.get("issues") or [],
        "recommendations": scores.get("recommendations") or [],
        "features": vision_features,
        "scores": scores,
    }

    # If vision_features contains `regions` or bounding boxes pass them through
    if isinstance(vision_features, dict):
        if "regions" in vision_features:
            response["regions"] = vision_features["regions"]
        # Azure may include objects/faces with bounding boxes; include lightweight normalization if present
        elif "objects" in vision_features:
            objs = []
            for o in vision_features.get("objects", [])[:8]:
                # attempt to normalize bounding boxes to x,y,w,h relative coords if available
                rect = o.get("rectangle") or o.get("boundingBox") or {}
                objs.append({"object": o.get("object") or o.get("name"), "rectangle": rect})
            response["regions"] = objs

    return response


# Routes to serve frontend pages (if frontend exists)
if FRONTEND_DIR.exists():
    @APP.get("/", include_in_schema=False)
    async def serve_cognitive_ui():
        index_file = FRONTEND_DIR / "cognitive_scan.html"
        if index_file.exists():
            return FileResponse(index_file)
        # fallback to /frontend listing or docs
        return RedirectResponse(url="/docs")

    @APP.get("/physical", include_in_schema=False)
    async def serve_physical_ui():
        index_file = FRONTEND_DIR / "physical_scan.html"
        if index_file.exists():
            return FileResponse(index_file)
        return RedirectResponse(url="/docs")


# Health root
@APP.get("/api/health")
async def health():
    return {"status": "ok", "service": "lifescan-backend"}


# Existing API endpoints (preserve original route names)
@APP.post("/api/scan/physical")
async def physical_scan(image: UploadFile = File(...)):
    """
    Accepts multipart/form-data with field "image".
    Returns normalized JSON for the frontend.
    """
    try:
        img_bytes = await _read_upload_file(image)
        # Vision analysis
        vision_features = analyze_image(img_bytes)

        # Domain logic
        scores = evaluate_physical_scan(vision_features)

        # Optional: generate human-friendly explanation via OpenAI wrapper
        explanation = generate_insights(scores)

        return JSONResponse(_shape_response("physical", vision_features, scores, explanation))
    except HTTPException:
        raise
    except Exception as exc:
        # log and return friendly error
        APP.logger = getattr(APP, "logger", None) or None
        if APP.logger:
            APP.logger.exception("physical_scan error")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(exc)}")


@APP.post("/api/scan/cognitive")
async def cognitive_scan(image: UploadFile = File(...)):
    try:
        img_bytes = await _read_upload_file(image)
        vision_features = analyze_image(img_bytes)
        scores = evaluate_cognitive_scan(vision_features)
        explanation = generate_insights(scores)
        return JSONResponse(_shape_response("cognitive", vision_features, scores, explanation))
    except HTTPException:
        raise
    except Exception as exc:
        if APP.logger:
            APP.logger.exception("cognitive_scan error")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(exc)}")


# Convenience endpoint used by older frontend that posts to /scan (defaults to cognitive)
@APP.post("/scan")
async def scan(image: UploadFile = File(...), mode: str = "cognitive"):
    """
    Convenience endpoint to support the frontend's default '/scan' path.
    Provide ?mode=physical to run physical pipeline.
    """
    mode = (mode or "cognitive").lower()
    if mode not in ("cognitive", "physical"):
        raise HTTPException(status_code=400, detail="mode must be 'cognitive' or 'physical'")

    if mode == "physical":
        return await physical_scan(image)
    return await cognitive_scan(image)


# Optional: provide a simple debug endpoint to accept image and return only vision features
@APP.post("/api/vision/debug")
async def vision_debug(image: UploadFile = File(...)):
    try:
        img_bytes = await _read_upload_file(image)
        features = analyze_image(img_bytes)
        return {"vision": features}
    except HTTPException:
        raise
    except Exception as exc:
        if APP.logger:
            APP.logger.exception("vision_debug error")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(exc)}")


# Run with: uvicorn backend.app_fastapi:APP --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app_fastapi:APP", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)
