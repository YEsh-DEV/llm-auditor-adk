"""PII sanitizer and input validation helper."""

import re
import yaml
from pathlib import Path
from typing import Dict, Any

# Compile regular expressions once for performance
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
API_KEY_REGEX = re.compile(
    r"\b(?:api[_-]?key|secret|token|password|passwd|auth)[_-]?(?:key|token)?\s*[:=]\s*['\"][a-zA-Z0-9\-_+=]{16,}['\"]",
    re.IGNORECASE
)

def load_policies() -> Dict[str, Any]:
    """Loads current policies from policies.yaml manifest."""
    # Look for policies.yaml in the package directory
    policy_path = Path(__file__).parent / "policies.yaml"
    if not policy_path.exists():
        policy_path = Path("policies.yaml")
        
    if not policy_path.exists():
        return {}
        
    try:
        with open(policy_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Warning: Failed to load policies.yaml: {e}")
        return {}

def sanitize_text(text: str) -> str:
    """Masks common PII patterns with placeholders."""
    sanitized = EMAIL_REGEX.sub("[REDACTED_EMAIL]", text)
    sanitized = PHONE_REGEX.sub("[REDACTED_PHONE]", sanitized)
    sanitized = API_KEY_REGEX.sub("[REDACTED_SECRET]", sanitized)
    return sanitized

def validate_and_sanitize(text: str) -> Dict[str, Any]:
    """
    Validates input structure and runs PII sanitization.
    Respects the pii_masking flag from policies.yaml.
    
    Returns:
        Dict containing validation 'status', 'sanitized_text', and 'pii_detected'.
    """
    if not text or not text.strip():
        return {
            "status": "FAIL",
            "sanitized_text": "",
            "pii_detected": False,
            "message": "Input draft is empty."
        }
        
    policies = load_policies()
    pii_masking_enabled = policies.get("global_structural_constraints", {}).get("pii_masking", True)
    
    if pii_masking_enabled:
        sanitized = sanitize_text(text)
        pii_detected = sanitized != text
    else:
        sanitized = text
        pii_detected = False
        
    return {
        "status": "PASS",
        "sanitized_text": sanitized,
        "pii_detected": pii_detected,
        "message": "Sanitization completed successfully."
    }
