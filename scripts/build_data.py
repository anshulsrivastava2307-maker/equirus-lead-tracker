#!/usr/bin/env python3
"""Build data.json for the Equirus Lead Tracker dashboard.

Rows are pipe-separated, 18 fields, taken from the tracker tab 'Digital Lead 2025':
row|date|appt|month|name|source|nr|country|vrm|lead_stage|deal_stage|exp_aum|total_aum|sugg_products|last_activity|last_activity_date|rm|remarks
(dates are Excel serials; text trimmed, tabs/newlines replaced by a space).

  --full FILE    replace every lead with these rows
  --delta FILE   upsert these rows into the existing leads
  --gone 1,2,3   sheet rows that no longer exist (removed)
  --asof ISO     refresh time (IST), default now
  --source-modified ISO  tracker's last-saved time from SharePoint
Field-level changes between the old and new data are appended to the change log.
"""
import argparse, datetime as dt, hashlib, json, os

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
FIELDS = ["row", "date", "appt", "month", "name", "source", "nr", "country", "vrm", "lead_stage", "deal_stage",
          "exp_aum", "total_aum", "sugg", "last_act", "last_act_date", "rm", "remarks"]
TRACK = {"source": "Source", "vrm": "VRM", "lead_stage": "Lead Stage", "deal_stage": "Deal Stage",
         "exp_aum": "Expected AUM", "total_aum": "Total AUM", "sugg": "Suggested Products", "rm": "RM Name",
         "name": "Name", "date": "Date", "month": "Month"}
SRC = {"instragram": "Instagram", "instagram": "Instagram", "facebook": "Facebook", "website": "Website",
       "google ads": "Google Ads", "google": "Google Ads", "organic": "Organic",
       "linkedin campaign": "LinkedIn", "linkedin": "LinkedIn", "existing fed client": "Existing Fed client"}
CHAN = {"Instagram": "Meta", "Facebook": "Meta"}
LS = {"closed": "Closed", "follow up": "Follow Up", "fwd to amc": "FWD to AMC", "call back": "Call Back",
      "unable to contact": "Unable to contact", "wrong number": "Wrong Number", "ibk": "IBK", "open": "Open",
      "contacted": "Contacted", "connected": "Connected", "qualified": "Qualified", "disqualified": "Disqualified",
      "": "Not updated"}
OPEN = {"Open", "Contacted", "Connected", "Call Back", "Follow Up", "Forwarded to Manish"}


def serial(v):
    try:
        f = float(v)
        return (dt.date(1899, 12, 30) + dt.timedelta(days=int(f))).isoformat() if 20000 < f < 80000 else None
    except Exception:
        return None


def outcome(ls, ds):
    d = ds.lower()
    if "won" in d: return "Won"
    if ls == "Qualified": return "Qualified - Lost" if "lost" in d else "Qualified - Active"
    if ls in OPEN: return "Follow-up"
    if ls == "Unable to contact": return "Unable to contact"
    if ls == "Closed": return "Closed - no response"
    if ls in ("FWD to AMC", "IBK"): return "Forwarded"
    if ls in ("Disqualified", "Wrong Number"): return "Disqualified"
    if ls == "Not updated": return "Not actioned"
    return "Follow-up"


def parse(fn):
    out = {}
    for line in open(fn, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        p = line.split("|")
        if len(p) != 18:
            raise SystemExit(f"Row has {len(p)} fields, expected 18: {line[:80]}")
        out[p[0]] = p
    return out


def rowhash(p):
    return hashlib.sha256("|".join(p).encode()).hexdigest()[:6]


def derive(p, today):
    r = dict(zip(FIELDS, p))
    ls = LS.get(r["lead_stage"].strip().lower(), r["lead_stage"].strip())
    src = SRC.get(r["source"].strip().lower(), r["source"].strip() or "Unknown")
    d = serial(r["date"]); m = serial(r["month"]); lad = serial(r["last_act_date"]) or serial(r["last_act"])
    out = outcome(ls, r["deal_stage"])
    age = (today - dt.date.fromisoformat(d)).days if d else None
    idle = (today - dt.date.fromisoformat(lad)).days if lad else None
    return {
        "row": int(r["row"]), "date": d, "month": (m or d or "")[:7], "name": r["name"].strip(),
        "source": src, "source_raw": r["source"], "channel": CHAN.get(src, src), "nr": r["nr"], "country": r["country"],
        "vrm": r["vrm"] if r["vrm"] not in ("", "-") else "Unassigned", "stage": ls, "deal_stage": r["deal_stage"],
        "exp_aum": r["exp_aum"], "total_aum": r["total_aum"], "products": r["sugg"], "last_activity": lad,
        "rm": r["rm"], "remarks": r["remarks"], "outcome": out, "age": age, "idle": idle, "raw": p,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data.json")
    ap.add_argument("--full"); ap.add_argument("--delta"); ap.add_argument("--gone", default="")
    ap.add_argument("--asof"); ap.add_argument("--source-modified")
    a = ap.parse_args()
    asof = dt.datetime.fromisoformat(a.asof) if a.asof else dt.datetime.now(IST)
    if asof.tzinfo is None: asof = asof.replace(tzinfo=IST)
    asof = asof.astimezone(IST)
    old = json.load(open(a.data, encoding="utf-8")) if os.path.exists(a.data) else {"leads": [], "changes": []}
    old_raw = {str(x["row"]): x["raw"] for x in old["leads"]}
    if a.full:
        new_raw = parse(a.full)
    else:
        new_raw = dict(old_raw)
        if a.delta:
            new_raw.update(parse(a.delta))
        for g in filter(None, a.gone.split(",")):
            new_raw.pop(g.strip(), None)
    changes = old.get("changes", [])
    when = asof.strftime("%Y-%m-%d %H:%M")
    if old_raw:
        for k in sorted(set(new_raw) | set(old_raw), key=int):
            n, o = new_raw.get(k), old_raw.get(k)
            nm = (n or o)[4].strip()
            if o is None:
                changes.append({"at": when, "row": int(k), "name": nm, "field": "New lead", "was": "",
                                "now": f"{SRC.get(n[5].strip().lower(), n[5])} / {n[9] or 'no stage yet'}"})
                continue
            if n is None:
                changes.append({"at": when, "row": int(k), "name": nm, "field": "Removed from tracker", "was": "", "now": ""})
                continue
            for i, f in enumerate(FIELDS):
                if f in TRACK and o[i].strip() != n[i].strip():
                    fmt = serial if f in ("date", "month") else (lambda v: v)
                    changes.append({"at": when, "row": int(k), "name": nm, "field": TRACK[f],
                                    "was": fmt(o[i]) or o[i] or "(blank)", "now": fmt(n[i]) or n[i] or "(blank)"})
            if o[17] != n[17]:
                added = n[17].startswith(o[17])
                changes.append({"at": when, "row": int(k), "name": nm, "field": "Remarks" if added else "Remarks (edited)",
                                "was": "" if added else o[17], "now": n[17][len(o[17]):].strip(" /-=") if added else n[17]})
    cutoff = (asof - dt.timedelta(days=90)).strftime("%Y-%m-%d")
    changes = [c for c in changes if c["at"] >= cutoff]
    leads = [derive(new_raw[k], asof.date()) for k in sorted(new_raw, key=int)]
    data = {"updated": asof.isoformat(timespec="minutes"), "source_modified": a.source_modified or old.get("source_modified"),
            "source": "Digital Inbound Lead Tracker Main.xlsx, tab 'Digital Lead 2025' (leads from 1 Sep 2026)",
            "leads": leads, "changes": changes}
    json.dump(data, open(a.data, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"{len(leads)} leads, {sum(1 for c in changes if c['at'] == when)} changes logged at {when}")


if __name__ == "__main__":
    main()
