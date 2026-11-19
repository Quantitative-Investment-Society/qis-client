# qis

The QIS club's market data, from the QIS data server (`https://data.qisumich.com`), as pandas or polars DataFrames. You need a key from Jasjit or Aadi.

```bash
pip install "qis[polars] @ git+https://github.com/Quantitative-Investment-Society/qis-client"
```

```python
import qis
qis.login("qis_...")          # once per computer; the key is saved in ~/.config/qis

qis.pm.markets("nba")                                  # every NBA market we collect
qis.pm.find("lakers")                                  # keyword search
qis.pm.rules("nba-lal-bos-2026-11-20")                 # how a market resolves
qis.pm.trades("nba-lal-bos-2026-11-20", start="2026-11-20")
qis.pm.trades("nba-lal-bos-2026-11-20", outcome="Celtics", start="2026-11-20")   # other side
qis.pm.book("nba-lal-bos-2026-11-20", levels=1, start="2026-11-20", end="2026-11-21")
qis.pm.fills("nba-lal-bos-2026-11-20", start="2026-11-20")                     # wallets + fees
```

Leagues for `markets()` and `find(league=...)`: `nfl`, `cfb`, `nba`, `cbb`, `mlb`, `nhl`, `soccer`, `ufc`, `f1`, `cricket`, `econ`, `weather`, `counts`, `companies`.

- `start` is inclusive, `end` is exclusive (dates like `"2026-11-20"`). Timestamps are UTC.
- `price` and `size` in trades come as strings: `df[["price", "size"]].astype(float)`.
- Order books are big: pass `start` and `end`. Ranges over 7 days are fetched in pieces.
- A market's two sides mirror each other; `outcome=` picks which side you see. Don't add them together.
- Data for finished days is cached in `~/.cache/qis`; `qis.clear_cache()` empties it.
- `engine="polars"` on any call returns polars.
- Missing data raises `FileNotFoundError`; other refusals raise `qis.QisError` with the reason.
- `qis.datasets()`, `qis.info(name)` and `qis.load(name, ...)` give raw access to every dataset your key can read.

Coming from `pmdata`: replace `pmdata.` with `qis.pm.` (`pmdata.load(channel, slug=...)` is `qis.pm.load(channel, slug, ...)`).

Settings: `QIS_API_KEY` and `QIS_URL` environment variables override the saved key and server; `QIS_CACHE` moves the cache.
