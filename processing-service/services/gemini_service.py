"""
Processing Service — Gemini AI Service
Calls Google Gemini API to analyse a complaint image and description.
Returns a deterministic JSON: {category, department, severity, estimatedCost, estimatedDuration, summary}.

Prompt engineering ensures Gemini ONLY returns raw JSON using predefined enums.
"""
import base64
import json
import logging
import re
from typing import Optional

logger = logging.getLogger("processing-service.gemini")

# ─── Valid enum values ────────────────────────────────────────────────────────

VALID_CATEGORIES = {
    "ROAD_DAMAGE", "WATER_LEAKAGE", "STREETLIGHT",
    "TRAFFIC_SIGNAL", "SEWERAGE", "GARBAGE", "TREE_FALL", "OTHER",
}

VALID_DEPARTMENTS = {
    "ROADS", "WATER", "ELECTRICITY", "TRAFFIC",
    "SANITATION", "SEWER", "PARKS", "OTHER",
}

# ─── Deterministic prompt ─────────────────────────────────────────────────────

SYSTEM_INSTRUCTION = """You are a civic complaint classification engine for a municipal management system.
Your ONLY task is to analyse a complaint and return a single valid JSON object.

STRICT OUTPUT RULES:
- Return ONLY a raw JSON object. Nothing else.
- No markdown. No code blocks. No explanation. No preamble. No trailing text.
- Start your response with {{ and end with }}.

JSON SCHEMA (all fields required):
{{
  "category": "<CATEGORY>",
  "department": "<DEPARTMENT>",
  "severity": <float 0.0-1.0>,
  "estimatedCost": <integer INR>,
  "estimatedDuration": "<string e.g. 2-3 days>",
  "summary": "<1-2 sentence description>"
}}

CATEGORY must be EXACTLY one of (uppercase, no synonyms):
ROAD_DAMAGE | WATER_LEAKAGE | STREETLIGHT | TRAFFIC_SIGNAL | SEWERAGE | GARBAGE | TREE_FALL | OTHER

DEPARTMENT must be EXACTLY one of (uppercase, no synonyms):
ROADS | WATER | ELECTRICITY | TRAFFIC | SANITATION | SEWER | PARKS | OTHER

CATEGORY → DEPARTMENT mapping (always follow this):
ROAD_DAMAGE → ROADS
WATER_LEAKAGE → WATER
STREETLIGHT → ELECTRICITY
TRAFFIC_SIGNAL → TRAFFIC
SEWERAGE → SEWER
GARBAGE → SANITATION
TREE_FALL → PARKS
OTHER → OTHER

severity: decimal between 0.0 (minor) and 1.0 (critical). Never use 0 or 1 exactly unless extreme.
estimatedCost: integer in Indian Rupees (no currency symbol, no commas).
estimatedDuration: human-readable duration like "1-2 days" or "1 week".
summary: factual, concise, 1-2 sentences describing the specific issue."""


PROMPT_TEMPLATE = """Analyse this civic complaint and classify it.

Complaint description: {description}

{image_note}

Return ONLY the JSON object. No other text."""


# ─── Gemini client ────────────────────────────────────────────────────────────

def _get_model():
    """Initialise Gemini model with system instruction for deterministic output."""
    import google.generativeai as genai
    from config import config

    if not config.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured")

    genai.configure(api_key=config.GEMINI_API_KEY)

    generation_config = {
        "temperature": 0.0,           # Fully deterministic
        "top_p": 1.0,
        "top_k": 1,
        "candidate_count": 1,
        "max_output_tokens": 256,
    }

    return genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config,
        system_instruction=SYSTEM_INSTRUCTION,
    )


# ─── JSON extraction ──────────────────────────────────────────────────────────

def _extract_json(text: str) -> Optional[dict]:
    """Extract and parse JSON from Gemini response. Handles edge cases robustly."""
    text = text.strip()

    # Attempt 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Attempt 2: Strip markdown code fences
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Attempt 3: Find first JSON object in response
    match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


# ─── Sanitisation ─────────────────────────────────────────────────────────────

def _sanitize(raw: dict) -> dict:
    """Validate and clamp all Gemini output fields to ensure correctness."""
    category = str(raw.get("category", "OTHER")).upper().strip()
    if category not in VALID_CATEGORIES:
        category = "OTHER"

    department = str(raw.get("department", "OTHER")).upper().strip()
    if department not in VALID_DEPARTMENTS:
        department = "OTHER"

    # Enforce correct department from category if mismatched
    CATEGORY_DEPT_MAP = {
        "ROAD_DAMAGE": "ROADS",
        "WATER_LEAKAGE": "WATER",
        "STREETLIGHT": "ELECTRICITY",
        "TRAFFIC_SIGNAL": "TRAFFIC",
        "SEWERAGE": "SEWER",
        "GARBAGE": "SANITATION",
        "TREE_FALL": "PARKS",
        "OTHER": "OTHER",
    }
    expected_dept = CATEGORY_DEPT_MAP.get(category)
    if expected_dept and department != expected_dept:
        logger.warning(
            f"Department mismatch for category={category}: got {department}, corrected to {expected_dept}"
        )
        department = expected_dept

    try:
        severity = float(raw.get("severity", 0.5))
        severity = round(max(0.01, min(0.99, severity)), 3)
    except (TypeError, ValueError):
        severity = 0.5

    try:
        estimated_cost = int(raw.get("estimatedCost", 0))
        estimated_cost = max(0, estimated_cost)
    except (TypeError, ValueError):
        estimated_cost = 5000

    estimated_duration = str(raw.get("estimatedDuration", "3-5 days")).strip() or "3-5 days"
    summary = str(raw.get("summary", "")).strip() or "Civic complaint submitted for assessment."

    return {
        "category": category,
        "department": department,
        "severity": severity,
        "estimatedCost": estimated_cost,
        "estimatedDuration": estimated_duration,
        "summary": summary,
    }


# ─── Main analysis function ───────────────────────────────────────────────────

def analyze_complaint(description: str, image_bytes: Optional[bytes] = None) -> dict:
    """
    Call Gemini API to classify a civic complaint.

    Args:
        description: Citizen-submitted text description.
        image_bytes: Raw image bytes from GCS (optional).

    Returns:
        Dict: {category, department, severity, estimatedCost, estimatedDuration, summary}
    """
    try:
        model = _get_model()
        image_note = "An image of the complaint site has also been provided." if image_bytes else ""
        prompt = PROMPT_TEMPLATE.format(description=description, image_note=image_note)

        contents = [prompt]

        if image_bytes:
            import google.generativeai as genai
            contents = [
                prompt,
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": base64.b64encode(image_bytes).decode("utf-8"),
                    }
                },
            ]

        response = model.generate_content(contents)
        raw_text = response.text.strip()
        logger.debug(f"Gemini raw response: {raw_text}")

        parsed = _extract_json(raw_text)
        if not parsed:
            logger.warning(f"Could not parse Gemini JSON response: {raw_text!r}")
            return _fallback_classification(description)

        result = _sanitize(parsed)
        logger.info(f"Gemini analysis complete: {result}")
        return result

    except Exception as exc:
        logger.error(f"Gemini API error: {exc}", exc_info=True)
        return _fallback_classification(description)


# ─── Keyword-based fallback ───────────────────────────────────────────────────

def _fallback_classification(description: str) -> dict:
    """
    Rule-based fallback classifier when Gemini is unavailable or returns invalid JSON.
    Maps keywords to predefined category/department enums.
    """
    desc_lower = description.lower()

    rules = [
        (["road", "pothole", "crack", "asphalt", "pavement", "highway", "tar"], "ROAD_DAMAGE", "ROADS", 0.6),
        (["water", "leak", "pipe", "flood", "drainage", "burst", "overflow"], "WATER_LEAKAGE", "WATER", 0.65),
        (["light", "streetlight", "lamp", "bulb", "dark", "power cut"], "STREETLIGHT", "ELECTRICITY", 0.5),
        (["traffic", "signal", "junction", "intersection", "light broken"], "TRAFFIC_SIGNAL", "TRAFFIC", 0.55),
        (["sewer", "manhole", "drain", "blockage", "sewage"], "SEWERAGE", "SEWER", 0.7),
        (["garbage", "waste", "trash", "dump", "litter", "rubbish"], "GARBAGE", "SANITATION", 0.45),
        (["tree", "branch", "fallen", "fall", "uprooted"], "TREE_FALL", "PARKS", 0.6),
    ]

    for keywords, category, department, severity in rules:
        if any(kw in desc_lower for kw in keywords):
            label = category.lower().replace("_", " ")
            return {
                "category": category,
                "department": department,
                "severity": severity,
                "estimatedCost": 5000,
                "estimatedDuration": "3-5 days",
                "summary": f"Civic complaint regarding {label} reported by a citizen requiring municipal attention.",
            }

    return {
        "category": "OTHER",
        "department": "OTHER",
        "severity": 0.4,
        "estimatedCost": 2000,
        "estimatedDuration": "1 week",
        "summary": "General civic complaint submitted for municipal review and assessment.",
    }
