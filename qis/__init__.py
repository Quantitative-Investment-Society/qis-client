"""QIS data: the club's market data from the QIS NAS.

    import qis
    qis.login("qis_...")              # once per computer, with the key you were given
    qis.datasets()                    # what your key can read
    qis.pm.find("lakers")             # prediction markets: see help(qis.pm)
    qis.load("polymarket.trades", instrument="nba-lal-bos-2026-11-20__Lakers",
             start="2026-11-20", end="2026-11-21")    # any dataset, raw

Data for days that are over is cached on your computer (~/.cache/qis), so
running a notebook again is instant and doesn't hit the server.
"""
from . import pm
from ._client import QisError, as_day, cache_dir, clear_cache, get_json, get_table, login, to_frame

__all__ = ["login", "me", "datasets", "info", "load", "pm", "cache_dir", "clear_cache", "QisError"]
__version__ = "0.1.0"


def me() -> dict:
    """Who your key belongs to and what it can read."""
    return get_json("/v1/me")


def datasets():
    """Datasets your key can read, as a DataFrame."""
    import pandas as pd
    return pd.DataFrame(get_json("/v1/datasets"))


def info(name: str) -> dict:
    """A dataset's description, columns and first/last day."""
    return get_json(f"/v1/datasets/{name}")


def load(name: str, instrument: str | None = None, start=None, end=None, columns=None,
         engine: str = "pandas", cache: bool = True):
    """Raw rows of any dataset. Daily datasets need start (inclusive) and end (exclusive)."""
    cols = ",".join(columns) if isinstance(columns, (list, tuple)) else columns
    params = {"instrument": instrument, "start": as_day(start), "end": as_day(end), "columns": cols}
    return to_frame(get_table(f"/v1/data/{name}", params, cache), engine)
