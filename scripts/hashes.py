#!/usr/bin/env python3
"""Print 'row:hash' for every lead in data.json (sha256 of the 18 pipe-joined raw fields, first 6 hex)."""
import hashlib, json, sys
d = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "data.json", encoding="utf-8"))
print(" ".join(f'{x["row"]}:{hashlib.sha256("|".join(x["raw"]).encode()).hexdigest()[:6]}' for x in d["leads"]))
