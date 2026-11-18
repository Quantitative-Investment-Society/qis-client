"""Prediction-market data (Polymarket via Telonex), same functions as the old pmdata.

    qis.pm.markets("nba")
    qis.pm.find("lakers")
    qis.pm.trades("nba-lal-bos-2026-11-20", start="2026-11-20")
    qis.pm.trades("nba-lal-bos-2026-11-20", outcome="Celtics", start="2026-11-20")   # the other side
    qis.pm.book("nba-lal-bos-2026-11-20", levels=1, start="2026-11-20", end="2026-11-21")

A binary market's two sides are mirror images (price -> 1 - p, buy <-> sell,
bids <-> asks). outcome= picks which side's view you get; don't add the two
together, it's the same trades twice. start is inclusive, end is exclusive.
"""
from __future__ import annotations

from datetime import date, timedelta

import pyarrow as pa

from ._client import as_day, get_json, get_table, to_frame

BOOK_MAX_DAYS = 7


def markets(league: str | None = None, engine: str = "pandas"):
    """Every market we collect (or one league: nfl, cfb, nba, cbb, mlb, nhl, soccer, ufc, f1, cricket),
    newest first. winner/settled_at are filled in once a market resolves."""
    return to_frame(get_table("/v1/pm/markets", {"league": league}, cache=False), engine)


def find(text: str, league: str | None = None, all: bool = False, limit: int = 50, engine: str = "pandas"):
    """Search question / slug / event title. all=True searches every Polymarket market (slow)."""
    return to_frame(get_table("/v1/pm/find", {"q": text, "league": league, "all": str(all).lower(),
                                              "limit": limit}, cache=False), engine)


def rules(slug: str) -> dict:
    """How a market resolves: description (the full rules), rules_url, resolution_source."""
    return get_json(f"/v1/pm/rules/{slug}")


def _params(outcome, start, end, **extra) -> dict:
    return {"outcome": None if outcome is None else str(outcome), "start": as_day(start), "end": as_day(end), **extra}


def trades(slug: str, outcome: str | int | None = None, start=None, end=None, engine: str = "pandas", cache: bool = True):
    """Every trade (price/size are strings, as Telonex sends them). Default: every day we have."""
    return to_frame(get_table(f"/v1/pm/trades/{slug}", _params(outcome, start, end), cache), engine)


def fills(slug: str, outcome: str | int | None = None, start=None, end=None, engine: str = "pandas", cache: bool = True):
    """On-chain fills: maker/taker wallets, taker fee, tx hashes. One row per maker filled."""
    return to_frame(get_table(f"/v1/pm/fills/{slug}", _params(outcome, start, end), cache), engine)


def _chunks(start, end):
    """Split [start, end) into pieces the server accepts (books: 7 days per request)."""
    s, e = as_day(start), as_day(end)
    if not s or not e:
        return [(s, e)]
    s, e = date.fromisoformat(s), date.fromisoformat(e)
    out = []
    while s < e:
        nxt = min(s + timedelta(days=BOOK_MAX_DAYS), e)
        out.append((s.isoformat(), nxt.isoformat()))
        s = nxt
    return out


def _book(path: str, slug, outcome, start, end, cache, **extra) -> pa.Table:
    parts = []
    for s, e in _chunks(start, end):
        try:
            parts.append(get_table(f"{path}/{slug}", _params(outcome, s, e, **extra), cache))
        except FileNotFoundError:
            if len(_chunks(start, end)) == 1:
                raise
    if not parts:
        raise FileNotFoundError(f"No order book stored for {slug!r} in [{as_day(start)}, {as_day(end)}).")
    return pa.concat_tables(parts, promote_options="default")


def book(slug: str, outcome: str | int | None = None, levels: int = 5, start=None, end=None,
         engine: str = "pandas", cache: bool = True):
    """Order book, one row per update, top `levels` per side as numbers, plus mid and spread.
    levels=1 = best bid/ask. Pass start and end; long ranges are fetched 7 days at a time."""
    return to_frame(_book("/v1/pm/book", slug, outcome, start, end, cache, levels=levels), engine)


def book_raw(slug: str, outcome: str | int | None = None, start=None, end=None, engine: str = "pandas", cache: bool = True):
    """The full nested book (every level), one row per book event. Big: pass a short range."""
    return to_frame(_book("/v1/pm/book_raw", slug, outcome, start, end, cache), engine)


def load(channel: str, slug: str, outcome: str | int | None = None, start=None, end=None,
         engine: str = "pandas", cache: bool = True):
    """pmdata.load() compatibility: channel = trades, book_snapshot_full or onchain_fills."""
    fn = {"trades": trades, "book_snapshot_full": book_raw, "onchain_fills": fills}.get(channel)
    if fn is None:
        raise ValueError("channel must be trades, book_snapshot_full or onchain_fills")
    return fn(slug, outcome=outcome, start=start, end=end, engine=engine, cache=cache)
