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
NODE_HEALTHCHECK_SCRIPT = """
const url = process.argv[1];
const timeoutMs = Number(process.argv[2] || 5000);
const controller = new AbortController();
const timer = setTimeout(() => controller.abort(), timeoutMs);
fetch(url, { signal: controller.signal })
  .then(async (response) => {
    clearTimeout(timer);
    const body = (await response.text()).slice(0, 1000);
    console.log(JSON.stringify({ statusCode: response.status, ok: response.ok, body }));
  })
  .catch((error) => {
    clearTimeout(timer);
    console.error(error && error.message ? error.message : String(error));
    process.exit(1);
  });
""".strip()
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


def mask_webhook_url(value: str) -> str:
    text = mask_remote_url(value)
    parsed = urlsplit(text)
    parts = parsed.path.split("/")
    for idx, part in enumerate(parts):
        if part == "tv" and idx + 2 < len(parts):
            parts[idx + 1] = "..."
    return urlunsplit((parsed.scheme, parsed.netloc, "/".join(parts), "", ""))


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
    health_path = "/health"
    if "/tv/" in parsed.path:
        base_path = parsed.path.split("/tv/", 1)[0].rstrip("/")
        health_path = f"{base_path}/health" if base_path else "/health"
    return urlunsplit((parsed.scheme, parsed.netloc, health_path, "", ""))


def http_health_status(url: str, *, timeout: int = 5) -> dict[str, Any]:
    if not url:
        return {"status": "skipped", "url": "", "message": "Keine URL gesetzt.", "information_only": True}
    try:
        with urlopen(url, timeout=timeout) as response:  # nosec - user-configured readiness endpoint
            body = response.read(1000).decode("utf-8", errors="replace")
            ok = 200 <= response.status < 300
    except (OSError, URLError) as exc:
        fallback = node_health_status(url, timeout=timeout)
        if fallback["status"] != "unreachable":
            fallback["python_message"] = str(exc)
            return fallback
        return {"status": "unreachable", "url": mask_remote_url(url), "message": str(exc), "node_fallback": fallback, "information_only": True}
    return {
        "status": "ok" if ok else "error",
        "url": mask_remote_url(url),
        "message": body,
        "information_only": True,
    }


def node_health_status(url: str, *, timeout: int = 5) -> dict[str, Any]:
    result = run_command(["node", "-e", NODE_HEALTHCHECK_SCRIPT, url, str(timeout * 1000)], timeout=timeout + 2)
    if not result["ok"]:
        return {
            "status": "unreachable",
            "url": mask_remote_url(url),
            "message": result["stderr"] or result["stdout"] or "Node health fallback failed.",
            "information_only": True,
        }
    try:
        payload = json.loads(result["stdout"])
    except json.JSONDecodeError:
        return {
            "status": "unreachable",
            "url": mask_remote_url(url),
            "message": "Node health fallback did not return JSON.",
            "information_only": True,
        }
    status_code = int(payload.get("statusCode", 0) or 0)
    return {
        "status": "ok" if 200 <= status_code < 300 else "error",
        "url": mask_remote_url(url),
        "message": str(payload.get("body", "")),
        "status_code": status_code,
        "fallback": "node_fetch",
        "information_only": True,
    }


def kas_bridge_status(env: dict[str, str], *, check_health: bool = False) -> dict[str, Any]:
    """Report whether a KAS/ALL-INKL webhook bridge is configured."""

    events_url = str(env.get("KAS_WEBHOOK_BRIDGE_EVENTS_URL", "")).strip()
    if not events_url:
        return {
            "status": "not_configured",
            "configured": False,
            "events_url": "",
            "message": "KAS Webhook Bridge ist nicht gesetzt.",
            "information_only": True,
        }
    parsed = urlsplit(events_url)
    valid = parsed.scheme == "https" and bool(parsed.netloc) and "/tv/" in parsed.path and parsed.path.rstrip("/").endswith("/events")
    health = (
        http_health_status(public_health_url_from_webhook(events_url))
        if check_health and valid
        else {"status": "skipped", "message": "KAS Healthcheck nicht angefordert.", "information_only": True}
    )
    health_ok = health["status"] == "ok" if check_health and valid else True
    return {
        "status": "configured" if valid and health_ok else "health_unreachable" if valid else "invalid",
        "configured": valid and health_ok,
        "events_url": mask_webhook_url(events_url),
        "message": (
            "KAS Webhook Bridge ist als dauerhafte HTTPS-Alternative konfiguriert."
            if valid and health_ok
            else "KAS Webhook Bridge ist formal gesetzt, aber der HTTPS-Healthcheck ist nicht erreichbar."
            if valid
            else "KAS_WEBHOOK_BRIDGE_EVENTS_URL muss eine HTTPS-URL mit /tv/<token>/events sein."
        ),
        "health": health,
        "information_only": True,
    }


def cloudflare_worker_bridge_status(env: dict[str, str], *, check_health: bool = False) -> dict[str, Any]:
    """Report whether a Cloudflare Worker webhook bridge is configured."""

    events_url = str(env.get("CLOUDFLARE_WORKER_BRIDGE_EVENTS_URL", "")).strip()
    if not events_url:
        return {
            "status": "not_configured",
            "configured": False,
            "events_url": "",
            "message": "Cloudflare Worker Bridge ist nicht gesetzt.",
            "information_only": True,
        }
    parsed = urlsplit(events_url)
    valid = parsed.scheme == "https" and bool(parsed.netloc) and "/tv/" in parsed.path and parsed.path.rstrip("/").endswith("/events")
    health = (
        http_health_status(public_health_url_from_webhook(events_url))
        if check_health and valid
        else {"status": "skipped", "message": "Worker Healthcheck nicht angefordert.", "information_only": True}
    )
    health_ok = health["status"] == "ok" if check_health and valid else True
    return {
        "status": "configured" if valid and health_ok else "health_unreachable" if valid else "invalid",
        "configured": valid and health_ok,
        "events_url": mask_webhook_url(events_url),
        "message": (
            "Cloudflare Worker Bridge ist als feste workers.dev-HTTPS-Inbox konfiguriert."
            if valid and health_ok
            else "Cloudflare Worker Bridge ist formal gesetzt, aber der HTTPS-Healthcheck ist nicht erreichbar."
            if valid
            else "CLOUDFLARE_WORKER_BRIDGE_EVENTS_URL muss eine HTTPS-URL mit /tv/<token>/events sein."
        ),
        "health": health,
        "information_only": True,
    }


def infrastructure_payload(
    *,
    env_file: Path = DEFAULT_ENV_PATH,
    check_public_health: bool = False,
) -> dict[str, Any]:
    tradingview = tradingview_readiness_payload(env_file=env_file)
    public_price = ""
    env: dict[str, str] = {}
    try:
        from trading_freaks.live_config import load_env_file

        env = load_env_file(env_file)
        public_price = env.get("TRADINGVIEW_WEBHOOK_PUBLIC_PRICE_URL", "")
    except (OSError, ImportError):
        public_price = ""

    public_health = (
        http_health_status(public_health_url_from_webhook(public_price))
        if check_public_health
        else {"status": "skipped", "message": "Public Healthcheck nicht angefordert.", "information_only": True}
    )
    git = git_status()
    cloudflare = cloudflare_auth_status()
    kas_bridge = kas_bridge_status(env, check_health=check_public_health)
    worker_bridge = cloudflare_worker_bridge_status(env, check_health=check_public_health)
    fixed_bridge_configured = bool(kas_bridge["configured"] or worker_bridge["configured"])
    cloudflare_required = not fixed_bridge_configured
    blockers = []
    if not git["remote_ready"]:
        blockers.append("GitHub Remote/Upstream fehlt.")
    if cloudflare_required and cloudflare["status"] != "authenticated":
        blockers.append("Dauerhafter Cloudflare Named Tunnel ist noch nicht authentifiziert.")
    if kas_bridge["status"] == "invalid" and not worker_bridge["configured"]:
        blockers.append("KAS Webhook Bridge ist ungueltig konfiguriert.")
    if kas_bridge["status"] == "health_unreachable" and not worker_bridge["configured"]:
        blockers.append("KAS Webhook Bridge ist gesetzt, aber HTTPS-Healthcheck ist nicht erreichbar.")
    if worker_bridge["status"] == "invalid" and not kas_bridge["configured"]:
        blockers.append("Cloudflare Worker Bridge ist ungueltig konfiguriert.")
    if worker_bridge["status"] == "health_unreachable" and not kas_bridge["configured"]:
        blockers.append("Cloudflare Worker Bridge ist gesetzt, aber HTTPS-Healthcheck ist nicht erreichbar.")
    if tradingview["status"] != "ready_for_tradingview":
        blockers.append("TradingView Public Webhooks sind noch nicht bereit.")
    if check_public_health and public_health["status"] != "ok":
        blockers.append("Public Webhook Healthcheck ist nicht erreichbar.")

    return {
        "status": "ready" if not blockers else "partial",
        "disclaimer": "Infrastrukturpruefung, keine Anlageberatung, keine Orderausfuehrung.",
        "git": git,
        "cloudflare": cloudflare,
        "kas_bridge": kas_bridge,
        "cloudflare_worker_bridge": worker_bridge,
        "tradingview_webhooks": tradingview,
        "public_health": public_health,
        "blockers": blockers,
        "next_steps": [
            "GitHub Remote setzen und pushen." if not git["remote_ready"] else "Git Remote regelmaessig pushen.",
            "Cloudflare Worker Bridge per workers.dev nutzen oder KAS HTTPS-Zertifikat aktivieren."
            if kas_bridge["status"] == "health_unreachable"
            else "Cloudflare Worker Bridge, KAS Bridge oder Cloudflare Named Tunnel als feste HTTPS-Bruecke konfigurieren."
            if cloudflare_required and cloudflare["status"] != "authenticated"
            else "Worker-/KAS-Bridge-Puller oder Named Tunnel im Tagesstart mitlaufen lassen.",
            "Erst nach erfolgreichem HTTPS-Healthcheck TradingView Alerts mit Public-Webhook-URLs anlegen/testen."
            if check_public_health and public_health["status"] != "ok"
            else "TradingView Alerts mit Public-Webhook-URLs anlegen/testen."
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
