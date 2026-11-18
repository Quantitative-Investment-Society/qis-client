"""HTTP, auth, caching and DataFrame conversion shared by every qis function."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
import pyarrow as pa
import pyarrow.ipc as ipc

DEFAULT_URL = "https://data.qisumich.com"
CONFIG = Path(os.environ.get("QIS_CONFIG") or Path.home() / ".config" / "qis" / "config.json")
CACHE = Path(os.environ.get("QIS_CACHE") or Path.home() / ".cache" / "qis")


class QisError(Exception):
    """The API refused a request (bad parameters, too large, no access...)."""


def _config() -> dict:
    try:
        return json.loads(CONFIG.read_text())
    except (FileNotFoundError, ValueError):
        return {}


def login(key: str, url: str | None = None) -> None:
    """Save your API key on this computer (once). Checks it works first."""
    cfg = {"key": key.strip(), "url": (url or _config().get("url") or DEFAULT_URL).rstrip("/")}
    r = httpx.get(f"{cfg['url']}/v1/me", headers={"Authorization": f"Bearer {cfg['key']}"}, timeout=30)
    if r.status_code != 200:
        raise QisError(_message(r))
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg))
    try:
        CONFIG.chmod(0o600)
    except OSError:
        pass
    me = r.json()
    print(f"Logged in as {me['name']} (access: {', '.join(me['groups'])}). Key saved to {CONFIG}")


def _settings() -> tuple[str, str]:
    cfg = _config()
    key = os.environ.get("QIS_API_KEY") or cfg.get("key")
    url = (os.environ.get("QIS_URL") or cfg.get("url") or DEFAULT_URL).rstrip("/")
    if not key:
        raise QisError('No API key yet. Run qis.login("qis_...") once with the key you were given.')
    return key, url


def _message(r: httpx.Response) -> str:
    try:
        return r.json().get("error") or r.text
    except ValueError:
        return f"HTTP {r.status_code}: {r.text[:300]}"


def _get(path: str, params: dict | None = None, timeout: float = 120) -> httpx.Response:
    key, url = _settings()
    params = {k: v for k, v in (params or {}).items() if v is not None}
    try:
        r = httpx.get(f"{url}{path}", params=params, headers={"Authorization": f"Bearer {key}"}, timeout=timeout)
    except httpx.TimeoutException:
        raise QisError("The request timed out. Ask for a shorter date range.") from None
    if r.status_code == 404:
        raise FileNotFoundError(_message(r))
    if r.status_code != 200:
        raise QisError(_message(r))
    return r


def get_json(path: str, params: dict | None = None):
    return _get(path, params).json()


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _cacheable(params: dict) -> bool:
    """Only data for days that are fully over never changes, so only that gets cached."""
    end = params.get("end")
    if not end:
        return False
    try:
        return date.fromisoformat(str(end)[:10]) <= _today() - timedelta(days=1)
    except ValueError:
        return False


def get_table(path: str, params: dict | None = None, cache: bool = True) -> pa.Table:
    params = {k: v for k, v in (params or {}).items() if v is not None}
    file = None
    if cache and _cacheable(params):
        _, url = _settings()
        h = hashlib.sha256(json.dumps([url, path, sorted(params.items())], default=str).encode()).hexdigest()[:32]
        file = CACHE / f"{h}.arrow"
        if file.exists():
            with pa.memory_map(str(file)) as src:
                return ipc.open_stream(src).read_all()
    r = _get(path, {**params, "format": "arrow"})
    table = ipc.open_stream(r.content).read_all()
    if file is not None:
        file.parent.mkdir(parents=True, exist_ok=True)
        tmp = file.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_bytes(r.content)
        os.replace(tmp, file)
    return table


def to_frame(table: pa.Table, engine: str = "pandas"):
    if engine == "polars":
        import polars as pl
        return pl.from_arrow(table)
    if engine == "arrow":
        return table
    if engine != "pandas":
        raise ValueError("engine must be pandas, polars or arrow")
    return table.to_pandas()


def as_day(d) -> str | None:
    """Accept '2026-11-20', date, datetime or pandas Timestamp."""
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.date().isoformat()
    if isinstance(d, date):
        return d.isoformat()
    if hasattr(d, "to_pydatetime"):
        return d.to_pydatetime().date().isoformat()
    return str(d).strip()[:10]


def cache_dir() -> Path:
    return CACHE


def clear_cache() -> None:
    import shutil
    shutil.rmtree(CACHE, ignore_errors=True)
