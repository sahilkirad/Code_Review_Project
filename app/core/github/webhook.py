"""
Webhook validation and parsing for GitHub webhooks
"""
import hmac
import hashlib
import json
import os
import logging
from typing import Optional, Dict, Any
from .models import WebhookPayload

logger = logging.getLogger(__name__)

def verify_webhook_signature(payload_body: bytes, signature_header: Optional[str]) -> bool:
    """
    Verify GitHub webhook signature using HMAC SHA256.
    
    Args:
        payload_body: Raw request body as bytes
        signature_header: X-Hub-Signature-256 header value
        
    Returns:
        True if signature is valid, False otherwise
    """
    if not signature_header:
        logger.warning("No signature header provided")
        return False
    
    webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if not webhook_secret:
        logger.error("GITHUB_WEBHOOK_SECRET environment variable not set")
        return False
    
    # GitHub sends signature as: sha256=<hash>
    if not signature_header.startswith("sha256="):
        logger.warning(f"Invalid signature format: {signature_header}")
        return False
    
    expected_signature = signature_header[7:]  # Remove "sha256=" prefix
    
    # Compute HMAC SHA256
    computed_signature = hmac.new(
        webhook_secret.encode('utf-8'),
        payload_body,
        hashlib.sha256
    ).hexdigest()
    
    # Use constant-time comparison to prevent timing attacks
    is_valid = hmac.compare_digest(computed_signature, expected_signature)
    
    if not is_valid:
        logger.warning("Webhook signature verification failed")
    
    return is_valid

def parse_webhook_payload(payload: Dict[str, Any]) -> Optional[WebhookPayload]:
    """
    Parse and validate webhook payload.
    
    Args:
        payload: JSON payload from GitHub
        
    Returns:
        WebhookPayload if valid, None otherwise
    """
    try:
        # Only process pull_request events
        if payload.get("action") not in ["opened", "synchronize", "reopened"]:
            logger.info(f"Ignoring webhook action: {payload.get('action')}")
            return None
        
        webhook_data = WebhookPayload(**payload)
        logger.info(f"Parsed webhook: PR #{webhook_data.pull_request.number} in {webhook_data.repository.full_name}")
        return webhook_data
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        return None

