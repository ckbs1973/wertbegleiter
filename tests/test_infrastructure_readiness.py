import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from check_infrastructure_readiness import (
    cloudflare_auth_status,
    infrastructure_payload,
    kas_bridge_status,
    mask_remote_url,
    mask_webhook_url,
    public_health_url_from_webhook,
)


class InfrastructureReadinessTests(unittest.TestCase):
    def test_mask_remote_url_removes_credentials(self):
        masked = mask_remote_url("https://user:secret-token@github.com/example/repo.git")

        self.assertEqual(masked, "https://github.com/example/repo.git")
        self.assertNotIn("secret-token", masked)

    def test_mask_webhook_url_removes_path_token(self):
        masked = mask_webhook_url("https://wertbegleiter.eu/wb/tv/abcdefghijklmnopqrstuvwxyz123456/events")

        self.assertEqual(masked, "https://wertbegleiter.eu/wb/tv/.../events")
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz123456", masked)

    def test_public_health_url_uses_origin_only(self):
        health = public_health_url_from_webhook("https://example.test/tv/abcdefghijklmnopqrstuvwxyz123456/price")

        self.assertEqual(health, "https://example.test/health")

    def test_cloudflare_auth_reports_missing_cert(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing_cert = Path(tmp) / "cert.pem"
            status = cloudflare_auth_status((missing_cert,))

        self.assertEqual(status["status"], "login_required")
        self.assertFalse(status["origin_cert_present"])
        self.assertTrue(status["information_only"])

    def test_public_health_failure_blocks_readiness_when_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text(
                "\n".join(
                    [
                        "TRADINGVIEW_WEBHOOK_LOCAL_PRICE_URL=http://127.0.0.1:8000/api/live-bridge/ingest",
                        "TRADINGVIEW_WEBHOOK_LOCAL_TRADE_URL=http://127.0.0.1:8000/api/trade-events/capture",
                        "TRADINGVIEW_WEBHOOK_TOKEN=abcdefghijklmnopqrstuvwxyz123456",
                        "TRADINGVIEW_WEBHOOK_PUBLIC_PRICE_URL=https://127.0.0.1.invalid/tv/abcdefghijklmnopqrstuvwxyz123456/price",
                        "TRADINGVIEW_WEBHOOK_PUBLIC_TRADE_URL=https://127.0.0.1.invalid/tv/abcdefghijklmnopqrstuvwxyz123456/trade",
                    ]
                ),
                encoding="utf-8",
            )

            with patch(
                "check_infrastructure_readiness.http_health_status",
                return_value={
                    "status": "unreachable",
                    "url": "https://example.invalid/health",
                    "message": "test failure",
                    "information_only": True,
                },
            ):
                payload = infrastructure_payload(env_file=env_file, check_public_health=True)

        self.assertEqual(payload["status"], "partial")
        self.assertIn("Public Webhook Healthcheck ist nicht erreichbar.", payload["blockers"])

    def test_kas_bridge_can_replace_cloudflare_requirement(self):
        with tempfile.TemporaryDirectory() as tmp:
            token = "abcdefghijklmnopqrstuvwxyz123456"
            env_file = Path(tmp) / ".env"
            env_file.write_text(
                "\n".join(
                    [
                        "TRADINGVIEW_WEBHOOK_LOCAL_PRICE_URL=http://127.0.0.1:8000/api/live-bridge/ingest",
                        "TRADINGVIEW_WEBHOOK_LOCAL_TRADE_URL=http://127.0.0.1:8000/api/trade-events/capture",
                        f"TRADINGVIEW_WEBHOOK_PUBLIC_PRICE_URL=https://wertbegleiter.eu/wb/tv/{token}/price",
                        f"TRADINGVIEW_WEBHOOK_PUBLIC_TRADE_URL=https://wertbegleiter.eu/wb/tv/{token}/trade",
                        f"KAS_WEBHOOK_BRIDGE_EVENTS_URL=https://wertbegleiter.eu/wb/tv/{token}/events",
                    ]
                ),
                encoding="utf-8",
            )

            with patch(
                "check_infrastructure_readiness.git_status",
                return_value={"remote_ready": True, "status": "ready", "information_only": True},
            ), patch(
                "check_infrastructure_readiness.cloudflare_auth_status",
                return_value={"status": "login_required", "information_only": True},
            ):
                payload = infrastructure_payload(env_file=env_file)

        self.assertEqual(payload["kas_bridge"]["status"], "configured")
        self.assertNotIn("Dauerhafter Cloudflare Named Tunnel ist noch nicht authentifiziert.", payload["blockers"])

    def test_kas_bridge_status_requires_events_route(self):
        status = kas_bridge_status({"KAS_WEBHOOK_BRIDGE_EVENTS_URL": "https://wertbegleiter.eu/wb/tv/token/price"})

        self.assertEqual(status["status"], "invalid")
        self.assertTrue(status["information_only"])


if __name__ == "__main__":
    unittest.main()
