import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from check_infrastructure_readiness import (
    cloudflare_auth_status,
    mask_remote_url,
    public_health_url_from_webhook,
)


class InfrastructureReadinessTests(unittest.TestCase):
    def test_mask_remote_url_removes_credentials(self):
        masked = mask_remote_url("https://user:secret-token@github.com/example/repo.git")

        self.assertEqual(masked, "https://github.com/example/repo.git")
        self.assertNotIn("secret-token", masked)

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


if __name__ == "__main__":
    unittest.main()
