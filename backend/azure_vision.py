def analyze_image(img_bytes: bytes):
    """
    Mock Azure Vision response.
    This will be replaced with real Azure Vision API later.
    """
    return {
        "color": {
            "dominantColorForeground": "White"
        },
        "faces": [
            {"age": 23}
        ]
    }
