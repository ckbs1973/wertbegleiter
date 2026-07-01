#!/usr/bin/env python3
"""Read-only infrastructure readiness check for daily operation.

The check reports Git, Cloudflare Tunnel, TradingView webhook, and local
service readiness. It never starts tunnels, never writes secrets, and never
executes broker orders.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any
from urllib.error import URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_tradingview_webhook_setup import readiness_payload as tradingview_readiness_payload


DEFAULT_ENV_PATH = ROOT / ".env"
CLOUDFLARE_CERT_PATHS = (
    Path.home() / ".cloudflared" / "cert.pem",
    Path.home() / ".cloudflare-warp" / "cert.pem",
    Path.home() / "cloudflare-warp" / "cert.pem",
    Path("/etc/cloudflared/cert.pem"),
    Path("/usr/local/etc/cloudflared/cert.pem"),
)


def run_command(args: list[str], *, cwd: Path = ROOT, timeout: int = 5) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            args,
            cwd=str(cwd),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "stdout": "", "stderr": str(exc), "returncode": -1}
    return {
        "ok": completed.returncode == 0,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "returncode": completed.returncode,
    }


def mask_remote_url(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    if "://" not in text:
        return text
    parsed = urlsplit(text)
    netloc = parsed.netloc
    if "@" in netloc:
        netloc = netloc.split("@", 1)[1]
    return urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))


def git_status(root: Path = ROOT) -> dict[str, Any]:
    inside = run_command(["git", "rev-parse", "--is-inside-work-tree"], cwd=root)
    if not inside["ok"] or inside["stdout"] != "true":
        return {
            "status": "not_configured",
            "inside_work_tree": False,
            "remote_ready": False,
            "message": "Lokales Git-Repository fehlt.",
            "information_only": True,
        }

    branch = run_command(["git", "branch", "--show-current"], cwd=root)
    head = run_command(["git", "rev-parse", "--short", "HEAD"], cwd=root)
    porcelain = run_command(["git", "status", "--short"], cwd=root)
    origin = run_command(["git", "remote", "get-url", "origin"], cwd=root)
    upstream = run_command(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], cwd=root)
    remote_url = mask_remote_url(origin["stdout"]) if origin["ok"] else ""
    dirty_lines = [line for line in porcelain["stdout"].splitlines() if line.strip()]
    upstream_name = upstream["stdout"] if upstream["ok"] else ""
    remote_ready = bool(remote_url and upstream_name)
    return {
        "status": "ready" if remote_ready and not dirty_lines else "remote_without_upstream" if remote_url and not upstream_name else "local_only" if not remote_url else "dirty",
        "inside_work_tree": True,
        "branch": branch["stdout"],
        "head": head["stdout"],
        "dirty_count": len(dirty_lines),
        "remote_configured": bool(remote_url),
        "remote_ready": remote_ready,
        "origin": remote_url,
        "upstream": upstream_name,
        "message": "Remote fehlt." if not remote_url else "Remote ist gesetzt, aber Push/Upstream fehlt." if not upstream_name else "Git Remote und Upstream sind gesetzt.",
        "information_only": True,
    }


def cloudflare_auth_status(cert_paths: tuple[Path, ...] = CLOUDFLARE_CERT_PATHS) -> dict[str, Any]:
    existing = [path for path in cert_paths if path.exists()]
    config_dir = Path.home() / ".cloudflared"
    named_tunnel_credentials = sorted(config_dir.glob("*.json")) if config_dir.exists() else []
    return {
        "status": "authenticated" if existing else "login_required",
        "origin_cert_present": bool(existing),
        "origin_cert_path": str(existing[0]) if existing else "",
        "named_tunnel_credentials_count": len(named_tunnel_credentials),
        "message": "Cloudflare Named Tunnel Auth ist vorhanden." if existing else "Cloudflare Login fehlt: cloudflared tunnel login ausfuehren.",
        "information_only": True,
    }


def public_health_url_from_webhook(value: str) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme != "https" or not parsed.netloc:
        return ""
    return urlunsplit((parsed.scheme, parsed.netloc, "/health", "", ""))


def http_health_status(url: str, *, timeout: int = 5) -> dict[str, Any]:
    if not url:
        return {"status": "skipped", "url": "", "message": "Keine URL gesetzt.", "information_only": True}
    try:
        with urlopen(url, timeout=timeout) as response:  # nosec - user-configured readiness endpoint
            body = response.read(1000).decode("utf-8", errors="replace")
            ok = 200 <= response.status < 300
    except (OSError, URLError) as exc:
        return {"status": "unreachable", "url": mask_remote_url(url), "message": str(exc), "information_only": True}
    return {
        "status": "ok" if ok else "error",
        "url": mask_remote_url(url),
        "message": body,
        "information_only": True,
    }


def infrastructure_payload(
    *,
    env_file: Path = DEFAULT_ENV_PATH,
    check_public_health: bool = False,
) -> dict[str, Any]:
    tradingview = tradingview_readiness_payload(env_file=env_file)
    public_price = ""
    try:
        from trading_freaks.live_config import load_env_file

        public_price = load_env_file(env_file).get("TRADINGVIEW_WEBHOOK_PUBLIC_PRICE_URL", "")
    except (OSError, ImportError):
        public_price = ""

    public_health = (
        http_health_status(public_health_url_from_webhook(public_price))
        if check_public_health
        else {"status": "skipped", "message": "Public Healthcheck nicht angefordert.", "information_only": True}
    )
    git = git_status()
    cloudflare = cloudflare_auth_status()
    blockers = []
    if not git["remote_ready"]:
        blockers.append("GitHub Remote/Upstream fehlt.")
    if cloudflare["status"] != "authenticated":
        blockers.append("Dauerhafter Cloudflare Named Tunnel ist noch nicht authentifiziert.")
    if tradingview["status"] != "ready_for_tradingview":
        blockers.append("TradingView Public Webhooks sind noch nicht bereit.")
    if check_public_health and public_health["status"] != "ok":
        blockers.append("Public Webhook Healthcheck ist nicht erreichbar.")

    return {
        "status": "ready" if not blockers else "partial",
        "disclaimer": "Infrastrukturpruefung, keine Anlageberatung, keine Orderausfuehrung.",
        "git": git,
        "cloudflare": cloudflare,
        "tradingview_webhooks": tradingview,
        "public_health": public_health,
        "blockers": blockers,
        "next_steps": [
            "GitHub Remote setzen und pushen." if not git["remote_ready"] else "Git Remote regelmaessig pushen.",
            "Cloudflare Named Tunnel Login/Config einrichten." if cloudflare["status"] != "authenticated" else "Named Tunnel Config und DNS-Route pruefen.",
            "TradingView Alerts mit Public-Webhook-URLs anlegen/testen."
            if tradingview["status"] == "ready_for_tradingview"
            else "TradingView Gateway/Tunnel/Webhook-URLs vervollstaendigen.",
        ],
        "information_only": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_PATH)
    parser.add_argument("--check-public-health", action="store_true")
    args = parser.parse_args()
    print(json.dumps(infrastructure_payload(env_file=args.env_file, check_public_health=args.check_public_health), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
