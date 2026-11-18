# qis

The QIS club's market data, from the QIS data server, as pandas or polars DataFrames.

```bash
pip install git+https://github.com/Quantitative-Investment-Society/qis-client
```

```python
import qis
qis.login("qis_...")          # once per computer, with the key Jasjit or Aadi gave you

qis.pm.markets("nba")                                  # every NBA market we collect
qis.pm.find("lakers")                                  # keyword search
qis.pm.rules("nba-lal-bos-2026-11-20")                 # how a market resolves
qis.pm.trades("nba-lal-bos-2026-11-20", start="2026-11-20")
qis.pm.trades("nba-lal-bos-2026-11-20", outcome="Celtics", start="2026-11-20")   # other side
qis.pm.book("nba-lal-bos-2026-11-20", levels=1, start="2026-11-20", end="2026-11-21")
qis.pm.fills("nba-lal-bos-2026-11-20", start="2026-11-20")                     # wallets + fees
```

- `start` is inclusive, `end` is exclusive (dates like `"2026-11-20"`). Timestamps are UTC.
- `price` and `size` in trades come as strings: `df[["price", "size"]].astype(float)`.
- Order books are big: pass `start` and `end`. Ranges over 7 days are fetched in pieces.
- Data for finished days is cached in `~/.cache/qis`; `qis.clear_cache()` empties it.
- `engine="polars"` on any call returns polars (`pip install "qis[polars] @ git+https://..."`).
- Missing data raises `FileNotFoundError`; other refusals raise `qis.QisError` with the reason.

Coming from `pmdata`: replace `pmdata.` with `qis.pm.` (`pmdata.load(channel, slug=...)` is `qis.pm.load(channel, slug, ...)`).
