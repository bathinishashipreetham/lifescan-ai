from fastapi import FastAPI, UploadFile, File
from dotenv import load_dotenv

from backend.azure_vision import analyze_image
from backend.azure_openai import generate_insights
from backend.physical_processing import evaluate_physical_scan
from backend.cognitive_processing import evaluate_cognitive_scan

load_dotenv()

app = FastAPI(title="LifeScan AI")

@app.get("/")
def root():
    return {"status": "LifeScan AI backend running"}

@app.post("/api/scan/physical")
async def physical_scan(image: UploadFile = File(...)):
    img_bytes = await image.read()

    vision_features = analyze_image(img_bytes)
    scores = evaluate_physical_scan(vision_features)
    explanation = generate_insights(scores)

    return {
        "mode": "physical",
        "features": vision_features,
        "scores": scores,
        "explanation": explanation
    }

@app.post("/api/scan/cognitive")
async def cognitive_scan(image: UploadFile = File(...)):
    img_bytes = await image.read()

    vision_features = analyze_image(img_bytes)
    scores = evaluate_cognitive_scan(vision_features)
    explanation = generate_insights(scores)

    return {
        "mode": "cognitive",
        "features": vision_features,
        "scores": scores,
        "explanation": explanation
    }
