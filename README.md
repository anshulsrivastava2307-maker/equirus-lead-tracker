# Equirus Lead Tracker

Password-protected dashboard of digital inbound leads (from 1 Sep 2026), read from
`Digital Inbound Lead Tracker Main.xlsx` (tab "Digital Lead 2025") on SharePoint.

- `index.html`: the dashboard (filters, KPIs, pipeline, charts, lead table, change log)
- `data.json`: lead data, rebuilt by the daily scheduled task. Do not edit by hand.
- `scripts/extract.js`: runs in Chrome on SharePoint, finds changed/new rows
- `scripts/build_data.py`: merges rows into data.json and logs field-level changes
- `scripts/hashes.py`: row fingerprints used by extract.js
- `middleware.js`: login (Vercel env `DASHBOARD_PASSWORD`, user `equirus` unless `DASHBOARD_USER` is set)

Email, phone and PAN from the tracker are never included.
