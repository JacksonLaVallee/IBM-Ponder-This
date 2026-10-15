Requires Python 3.10+, an NVIDIA GPU/driver, and Visual Studio C++ Build Tools on Windows.

```sh
cd 2026/09-Sep
python -m pip install -r requirements.txt
python build.py
python search.py --budget 86400
```

On an RTX 4070 Ti SUPER (16 GB), allow roughly **7–10 hours** for the included search. Its original search domains used 6.83 hours of compute; total runtime varies. Rerun the same command to resume saved progress.

To replay only the known successful range: `python search.py --replay-hit --chunk 60` — about **10 seconds** on that GPU. This is a targeted replay, not a new discovery.

To verify all 57 saved integer witnesses: `python verify.py` — under **0.1 seconds**, no GPU required.
