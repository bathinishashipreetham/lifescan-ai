def evaluate_cognitive_scan(features: dict):
    age = features["faces"][0]["age"]

    stress_score = 0.8 if age > 20 else 0.4

    return {
        "stress_score": stress_score,
        "cognitive_load": "high" if stress_score > 0.6 else "normal"
    }
