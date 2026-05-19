"""Webhook signature verification for Meta WhatsApp Cloud API."""

import hashlib
import hmac


def verify_webhook_signature(
    payload: bytes,
    signature_header: str | None,
    app_secret: str,
) -> bool:
    """
    Verify X-Hub-Signature-256 from Meta.

    Header format: sha256=<hex_digest>
    """
    if not signature_header or not app_secret:
        return False

    expected_prefix = "sha256="
    if not signature_header.startswith(expected_prefix):
        return False

    received_sig = signature_header[len(expected_prefix) :]
    computed = hmac.new(
        app_secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(received_sig, computed)
