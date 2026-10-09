"""Download the full Études en France catalogue (list + every program's detail).

Usage: python scripts/fetch_catalogue.py            # list + details (resumes from cache)
"""
import concurrent.futures as cf
import datetime as dt
import http.cookiejar
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIST = ROOT / "data/cache/list.json"
DETAIL = ROOT / "data/cache/details.jsonl"
BASE = "https://etudesenfrance.diplomatie.gouv.fr"
API = BASE + "/parcours-api/public/catalogue/formations"

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
UA = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}


def token():
    for url in (BASE + "/catalogue-formations", API + "/filters/formations"):
        try:
            opener.open(urllib.request.Request(url, headers=UA), timeout=30).read()
        except Exception:
            pass
    return next((c.value for c in jar if c.name == "XSRF-TOKEN"), "")


def fetch_list():
    """Page through the search API, 100 per page. Progress is saved so a rerun resumes."""
    part = ROOT / "data/cache/list.partial.json"
    state = json.loads(part.read_text(encoding="utf-8")) if part.exists() else {"page": 1, "items": []}
    tok, page, out = token(), state["page"], state["items"]
    while True:
        body = json.dumps({"page": page, "size": 100}).encode()
        for attempt in range(30):
            try:
                req = urllib.request.Request(API, data=body, method="POST",
                                             headers={**UA, "Content-Type": "application/json", "X-XSRF-TOKEN": tok})
                raw = opener.open(req, timeout=60).read().decode("utf-8")
                if raw.lstrip().startswith("{"):
                    data = json.loads(raw)
                    break
            except Exception:
                pass
            time.sleep(min(20 + attempt * 20, 180))  # portal shows a maintenance page when we go too fast
            tok = token()
        else:
            raise SystemExit(f"list page {page} failed – rerun to resume")
        out += data["donnees"]
        n = data["pagination"]["nbPages"]
        part.write_text(json.dumps({"page": page + 1, "items": out}, ensure_ascii=False), encoding="utf-8")
        if page % 10 == 0:
            print(f"  list page {page}/{n}", flush=True)
        if page >= n:
            break
        page += 1
        time.sleep(1)
    LIST.write_text(json.dumps({"fetched": dt.date.today().isoformat(), "items": out}, ensure_ascii=False), encoding="utf-8")
    part.unlink()
    print("list:", len(out))
    return out


def detail(key):
    url = f"{API}/{key[0]}/site/{key[1]}"
    err = "?"
    for attempt in range(10):
        try:
            body = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read().decode("utf-8")
            if body.lstrip().startswith("{"):
                return key, json.loads(body)
            err = "maintenance"
            time.sleep(30 + attempt * 30)
            continue
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                return key, {"__error": e.code}
            err = str(e.code)
        except Exception as e:
            err = type(e).__name__
        time.sleep(2 + attempt * 2)
    return key, {"__error": err}


def fetch_details(items):
    done = set()
    if DETAIL.exists():
        for line in DETAIL.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if "__error" not in r["d"]:
                done.add(r["k"])
    keys = sorted({f"{i['idFormation']}/{i['idSite']}" for i in items} - done)
    print("details to fetch:", len(keys), flush=True)
    with DETAIL.open("a", encoding="utf-8") as f, cf.ThreadPoolExecutor(4) as ex:
        for n, (k, d) in enumerate(ex.map(detail, [tuple(k.split("/")) for k in keys])):
            f.write(json.dumps({"k": "/".join(k), "d": d}, ensure_ascii=False) + "\n")
            if n % 500 == 0:
                f.flush()
                print(f"  details {n}/{len(keys)}", flush=True)


if __name__ == "__main__":
    items = json.loads(LIST.read_text(encoding="utf-8"))["items"] if LIST.exists() else fetch_list()
    fetch_details(items)
    print("done")
