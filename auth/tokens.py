"""
Token System — JWT-based Master/Device/Session tokens.
HMAC-SHA256 signing for security.
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
    - Master Token  : permanent, user identity (keep safe)
    - Device Token  : per-device, auto-generated, 1 year
    - Session Token : temporary, 24 hours
    """

    def __init__(self, secret_key: str = None):
        self.secret = secret_key or os.environ.get(
            "COBWEAVERCLAW_SECRET",
            hashlib.sha256(os.urandom(32)).hexdigest()
        )

    def create_master_token(self, user_id: str) -> str:
        """Create a permanent master token for a user."""
        payload = {
            "user_id": user_id,
            "type":    "master",
            "created": datetime.utcnow().isoformat()
        }
        return self._sign(payload)

    def create_device_token(self, master_token: str, device_id: str) -> str:
        """Create a device-specific token derived from master token."""
        master_payload = self.verify(master_token)
        if not master_payload:
            raise ValueError("Invalid or expired master token")
        payload = {
            "user_id":   master_payload["user_id"],
            "device_id": device_id,
            "type":      "device",
            "created":   datetime.utcnow().isoformat(),
            "expires":   (datetime.utcnow() + timedelta(days=365)).isoformat()
        }
        return self._sign(payload)

    def create_session_token(self, device_token: str) -> str:
        """Create a 24-hour session token."""
        device_payload = self.verify(device_token)
        if not device_payload:
            raise ValueError("Invalid device token")
        payload = {
            "user_id":   device_payload["user_id"],
            "device_id": device_payload.get("device_id"),
            "type":      "session",
            "created":   datetime.utcnow().isoformat(),
            "expires":   (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }
        return self._sign(payload)

    def verify(self, token: str) -> dict | None:
        """Verify token signature. Returns payload dict or None."""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            header, body, sig = parts

            # Re-compute signature
            msg      = f"{header}.{body}".encode()
            key      = self.secret.encode()
            expected = hmac.new(key, msg, hashlib.sha256).digest()          # FIX: correct usage
            expected_b64 = base64.urlsafe_b64encode(expected).decode().rstrip("=")

            # Constant-time comparison (prevents timing attacks)
            if not hmac.compare_digest(sig, expected_b64):
                return None

            # Decode payload
            padded  = body + "=" * (-len(body) % 4)
            payload = json.loads(base64.urlsafe_b64decode(padded))

            # Check expiry if present
            if "expires" in payload:
                expires = datetime.fromisoformat(payload["expires"])
                if datetime.utcnow() > expires:
                    return None

            return payload
        except Exception:
            return None

    def revoke(self, token: str) -> bool:
        """
        Mark token as revoked.
        (Stored in SQLite revocation list — Phase 2)
        """
        # Phase 2: implement revocation list in SQLite
        return True

    def _sign(self, payload: dict) -> str:
        """Sign a payload and return JWT-style token string."""
        header_b64  = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').decode().rstrip("=")
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",",":")).encode()
        ).decode().rstrip("=")

        msg     = f"{header_b64}.{payload_b64}".encode()
        key     = self.secret.encode()
        sig_raw = hmac.new(key, msg, hashlib.sha256).digest()
        sig_b64 = base64.urlsafe_b64encode(sig_raw).decode().rstrip("=")

        return f"{header_b64}.{payload_b64}.{sig_b64}"
