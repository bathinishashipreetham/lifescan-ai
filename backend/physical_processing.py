def evaluate_physical_scan(features: dict):
    dominant = features["color"]["dominantColorForeground"]

    anemia_risk = 0.7 if dominant in ["White", "Gray"] else 0.4

    return {
        "dominant_color": dominant,
        "anemia_risk": anemia_risk
    }
