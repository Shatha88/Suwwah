import requests
from pathlib import Path

RAW_URL = "https://raw.githubusercontent.com/eligugliotta/SAND/master/SAND_texts.tsv"

out = Path("data")
out.mkdir(parents=True, exist_ok=True)
target = out / "SAND_texts.tsv"

r = requests.get(RAW_URL, timeout=20)
r.raise_for_status()
target.write_bytes(r.content)

print("Downloaded:", target)