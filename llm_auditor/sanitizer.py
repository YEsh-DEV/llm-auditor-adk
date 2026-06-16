# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""PII sanitizer and input validation helper."""

import re
from typing import Dict, Any

# Compile regular expressions once for performance
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
API_KEY_REGEX = re.compile(
    r"\b(?:api[_-]?key|secret|token|password|passwd|auth)[_-]?(?:key|token)?\s*[:=]\s*['\"][a-zA-Z0-9\-_+=]{16,}['\"]",
    re.IGNORECASE
)

def sanitize_text(text: str) -> str:
    """Masks common PII patterns with placeholders."""
    sanitized = EMAIL_REGEX.sub("[REDACTED_EMAIL]", text)
    sanitized = PHONE_REGEX.sub("[REDACTED_PHONE]", sanitized)
    sanitized = API_KEY_REGEX.sub("[REDACTED_SECRET]", sanitized)
    return sanitized

def validate_and_sanitize(text: str) -> Dict[str, Any]:
    """
    Validates input structure and runs PII sanitization.
    
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
        
    sanitized = sanitize_text(text)
    pii_detected = sanitized != text
    
    return {
        "status": "PASS",
        "sanitized_text": sanitized,
        "pii_detected": pii_detected,
        "message": "Sanitization completed successfully."
    }
