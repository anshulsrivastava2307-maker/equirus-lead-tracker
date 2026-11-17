// Run in a Chrome tab on https://equiruswealth-my.sharepoint.com/personal/varun_bhardwaj_equiruswealth_com/...
// Before running, replace __OLD_HASHES__ below with the output of `python3 scripts/hashes.py`.
// Reads the tracker straight from SharePoint, compares every row with the dashboard's current data,
// and keeps only changed/new rows in window.__chunks (900-char pieces) for transfer.
const OLD = Object.fromEntries("__OLD_HASHES__".trim().split(/\s+/).filter(Boolean).map(x => x.split(":")));
const FILE_ID = "6df7bac5-361b-4837-861d-f57b15dc67f8";
const base = `/personal/varun_bhardwaj_equiruswealth_com/_api/web/GetFileById('${FILE_ID}')`;
const meta = await (await fetch(base + "?$select=TimeLastModified", {headers: {Accept: "application/json;odata=nometadata"}, cache: "no-store"})).json();
const buf = new Uint8Array(await (await fetch(base + "/$value", {cache: "no-store"})).arrayBuffer());
const dv = new DataView(buf.buffer), td = new TextDecoder();
let eocd = -1; for (let i = buf.length - 22; i >= 0; i--) { if (dv.getUint32(i, true) === 0x06054b50) { eocd = i; break; } }
const cnt = dv.getUint16(eocd + 10, true); let o = dv.getUint32(eocd + 16, true); const files = {};
for (let k = 0; k < cnt; k++) { const method = dv.getUint16(o + 10, true), csize = dv.getUint32(o + 20, true), nl = dv.getUint16(o + 28, true), el = dv.getUint16(o + 30, true), cl = dv.getUint16(o + 32, true), lho = dv.getUint32(o + 42, true); files[td.decode(buf.slice(o + 46, o + 46 + nl))] = {method, csize, lho}; o += 46 + nl + el + cl; }
async function read(n) { const f = files[n]; const ln = dv.getUint16(f.lho + 26, true), le = dv.getUint16(f.lho + 28, true); const d = buf.slice(f.lho + 30 + ln + le, f.lho + 30 + ln + le + f.csize); if (f.method === 0) return td.decode(d); return await new Response(new Blob([d]).stream().pipeThrough(new DecompressionStream("deflate-raw"))).text(); }
const wb = await read("xl/workbook.xml"), rels = await read("xl/_rels/workbook.xml.rels");
const sheets = [...wb.matchAll(/<sheet [^>]*name="([^"]+)"[^>]*r:id="([^"]+)"/g)].map(m => [m[1], m[2]]);
const relmap = Object.fromEntries([...rels.matchAll(/Id="([^"]+)"[^>]*Target="([^"]+)"/g)].map(m => [m[1], m[2]]));
const target = sheets.find(s => /digital lead/i.test(s[0]));
const dp = new DOMParser();
const ssx = dp.parseFromString(await read("xl/sharedStrings.xml"), "application/xml");
const ss = [...ssx.getElementsByTagName("si")].map(si => [...si.getElementsByTagName("t")].map(t => t.textContent).join(""));
const sx = dp.parseFromString(await read("xl/" + relmap[target[1]].replace(/^\/?xl\//, "")), "application/xml");
const ci = c => { let n = 0; for (const ch of c.replace(/\d+/g, "")) n = n * 26 + ch.charCodeAt(0) - 64; return n - 1; };
const rows = [];
for (const rw of sx.getElementsByTagName("row")) { const rn = +rw.getAttribute("r"); const a = []; for (const c of rw.getElementsByTagName("c")) { const t = c.getAttribute("t"); const v = c.getElementsByTagName("v")[0]; let val = v ? v.textContent : ""; if (t === "s") val = ss[+val]; else if (t === "inlineStr") val = [...c.getElementsByTagName("t")].map(x => x.textContent).join(""); a[ci(c.getAttribute("r"))] = val; } if (a.some(x => x !== undefined && x !== "")) rows.push([rn, ...Array.from(a, x => x ?? "")]); }
const header = rows[0].slice(1).join("|");
const EXPECTED = "Date|Appointment Data|Month|Lead Age Since Received|Lead Age Since Appointment|Lead ID|Name|Email|Phone Number|Source|PAN Number|NR Status|Country|VRM Name|Lead Stage|Deal Stage|Expected AUM|Total AUM|AUM IN Cr|Suggested Products|Last Activity|Last Activity Date|Days Since Last Activity|RM Meeting Date|Days since RM Appointment|RM Name|RM Meeting Status|Detailed Remarks|Lost Reason|New Feedback Remark by VRM";
const inRange = v => /^\d+(\.\d+)?$/.test(v) && +v >= 46266; // on/after 1 Sep 2026
const cand = rows.slice(1).filter(r => inRange(r[1]) || inRange(r[3]));
const clean = x => ((x ?? "") + "").replace(/[\t\n\r|]+/g, " ").trim();
const P = [0, 1, 2, 3, 7, 10, 12, 13, 14, 15, 16, 17, 18, 20, 21, 22, 26, 28];
const enc = new TextEncoder();
const h = async s => [...new Uint8Array(await crypto.subtle.digest("SHA-256", enc.encode(s)))].slice(0, 3).map(b => b.toString(16).padStart(2, "0")).join("");
const changed = [], added = [], pick = [], hashes = [], cur = {};
for (const r of cand) { const line = P.map(i => clean(r[i])).join("|"); const k = String(r[0]); const hh = await h(line); cur[k] = 1;
  if (!OLD[k]) added.push(k); else if (OLD[k] !== hh) changed.push(k); else continue;
  pick.push(line); hashes.push(k + ":" + hh); }
const gone = Object.keys(OLD).filter(k => !cur[k]);
const s = pick.join("\n"); const chunks = []; for (let i = 0; i < s.length; i += 900) chunks.push(s.slice(i, i + 900));
window.__chunks = chunks;
({modified: meta.TimeLastModified, headerOK: header === EXPECTED, total: cand.length, changed, added, gone, hashes: hashes.join(" "), chunks: chunks.length})
