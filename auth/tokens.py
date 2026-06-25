"""
Token System — JWT-based Master/Device/Session tokens.
"""
import hashlib
import hmac
import base64
import json
import os
from datetime import datetime, timedelta


class TokenManager:
    """
    Three-tier token system:
    - Master Token: permanent, user identity
    - Device Token: per-device, auto-generated
    - Session Token: temporary, 24-hour
    """

    def __init__(self, secret_key: str = None):
        self.secret = secret_key or os.environ.get(
            "COBWEAVERCLAW_SECRET",
            hashlib.sha256(os.urandom(32)).hexdigest()
        )

    def create_master_token(self, user_id: str) -> str:
        """Create a permanent master token for a user."""
        payload = {"user_id": user_id, "type": "master",
                   "created": datetime.utcnow().isoformat()}
        return self._sign(payload)

    def create_device_token(self, master_token: str, device_id: str) -> str:
        """Create a device-specific token from a master token."""
        master_payload = self._verify(master_token)
        if not master_payload:
            raise ValueError("Invalid master token")
        payload = {
            "user_id":   master_payload["user_id"],
            "device_id": device_id,
            "type":      "device",
            "created":   datetime.utcnow().isoformat(),
            "expires":   (datetime.utcnow() + timedelta(days=365)).isoformat()
        }
        return self._sign(payload)

    def verify(self, token: str) -> dict | None:
        """Verify and decode a token. Returns payload or None."""
        return self._verify(token)

    def _sign(self, payload: dict) -> str:
        header  = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip("=")
        body    = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        sig_raw = hmac.new(self.secret.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
        sig     = base64.urlsafe_b64encode(sig_raw).decode().rstrip("=")
        return f"{header}.{body}.{sig}"

    def _verify(self, token: str) -> dict | None:
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            header, body, sig = parts
            expected = hmac.new(
                self.secret.encode(),
                f"{header}.{body}".encode(),
                hashlib.sha256
            ).digest()
            expected_sig = base64.urlsafe_b64encode(expected).decode().rstrip("=")
            if not hmac.compare_digest(sig, expected_sig):
                return None
            payload = json.loads(base64.urlsafe_b64decode(body + "=="))
            return payload
        except Exception:
            return None
