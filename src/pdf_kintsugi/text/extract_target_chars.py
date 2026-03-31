def extract_target_chars(chars: list[dict], bbox: tuple) -> list[dict]:
    extracted_chras: list[dict] = [
        ch
        for ch in chars
        if bbox[0] <= ch["x"] < bbox[2] and bbox[1] <= ch["y"] < bbox[3]
    ]

    return extracted_chras
