"""Build data/catalogue.js from the downloaded Études en France catalogue.

Run scripts/fetch_catalogue.py first (it caches data/cache/list.json + details.jsonl).
"""
import datetime as dt
import html
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIST = ROOT / "data/cache/list.json"
DETAIL = ROOT / "data/cache/details.jsonl"
OUT = ROOT / "data/catalogue.js"

LANG = {"Français": "French", "Anglais": "English", "Français et anglais": "French & English", "Anglais et français": "French & English"}
TESTS = [
    ("IELTS", r"\bIELTS\b"), ("TOEFL", r"\bTOEFL\b"), ("PTE", r"\bPTE\b|Pearson Test"),
    ("TOEIC", r"\bTOEIC\b"), ("Cambridge", r"Cambridge|\b(?:FCE|CAE|CPE)\b|Linguaskill"), ("Duolingo", r"Duolingo"),
]
MOI = re.compile(
    r"medium of instruction|\bMOI\b|(?:previous|prior|bachelor'?s?)\s+(?:studies|degree|education)[^.]{0,60}(?:taught\s+)?in English|"
    r"(?:degree|studies|diploma)\s+(?:was\s+|were\s+)?(?:fully\s+|entirely\s+)?taught in English|"
    r"(?:études|diplôme|formation) ant[ée]rieures?[^.]{0,40}en anglais|attestation[^.]{0,60}(?:enseignement|langue)[^.]{0,30}anglais",
    re.I,
)
ENG_LEVEL = re.compile(r"(?:anglais|english)[^.;]{0,50}\b(B1|B2|C1|C2)\b|\b(B1|B2|C1|C2)\b[^.;]{0,40}(?:anglais|english)", re.I)
FR_LEVEL = re.compile(r"DELF|DALF|TCF|TEF\b|(?:fran[cç]ais|french)[^.;]{0,50}\b(A2|B1|B2|C1|C2)\b|\b(A2|B1|B2|C1|C2)\b[^.;]{0,40}(?:fran[cç]ais|french)", re.I)


def clean(s):
    if isinstance(s, dict):
        s = s.get("value")
    if not s:
        return ""
    s = re.sub(r"<br\s*/?>|</p>|</li>", " ", s)
    s = re.sub(r"<[^>]+>", "", s)
    return " ".join(html.unescape(s).split())


def english_rules(text):
    tests = [name for name, pat in TESTS if re.search(pat, text, re.I)]
    m = re.search(r"\bIELTS\b[^0-9]{0,30}(\d(?:[.,]\d)?)", text, re.I)
    ielts = m.group(1).replace(",", ".") if m and 4 <= float(m.group(1).replace(",", ".")) <= 9 else None
    lvl = ENG_LEVEL.search(text)
    kind = "moi" if MOI.search(text) else "test" if tests else "level" if lvl else "none"
    out = {"k": kind}
    if tests:
        out["t"] = tests
    if ielts:
        out["i"] = ielts
    if lvl:
        out["l"] = lvl.group(1) or lvl.group(2)
    return out


def city_of(address):
    for line in reversed((address or "").strip().splitlines()):
        m = re.search(r"\b\d{5}\s+([^\d,]+)", line)
        if m:
            return re.sub(r"\bcedex\b.*", "", m.group(1), flags=re.I).strip(" ,-").title()
    return ""


def city_from_site(site):
    m = re.match(r"(?:site|campus|p[oô]le)\s+(?:universitaire\s+)?(?:de |d'|du |des )\s*(.+)", site or "", re.I)
    if m and not re.search(r"\d|rue|avenue|bâtiment|batiment", m.group(1), re.I):
        return m.group(1).strip()
    return ""


def lvl_num(v):
    m = re.search(r"\+(\d)", v or "")
    return int(m.group(1)) if m else None


def build():
    lst = json.loads(LIST.read_text(encoding="utf-8"))
    details = {}
    if DETAIL.exists():
        for line in DETAIL.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r["k"] not in details or "__error" in details[r["k"]]:
                details[r["k"]] = r["d"]

    rows, seen = [], set()
    for it in lst["items"]:
        key = f"{it['idFormation']}/{it['idSite']}"
        if key in seen:
            continue
        seen.add(key)
        d = details.get(key, {})
        ok = "formationInformationGenerale" in d
        g = d.get("formationInformationGenerale", {}) if ok else {}
        E = d.get("formationsInformationsEntree", []) if ok else []
        contact = d.get("siteInformationContact", {}) if ok else {}
        req = clean(g.get("preRequis"))
        proc = " ".join(clean(e.get("procedureInscription")) for e in E)
        text = " ".join([req, clean(g.get("descriptionFormation")), proc])
        years = [[e["annee"], e.get("valeurComNiveau"), 0 if e["ferme"] else 1, int(e["coutFormation"]) if e.get("coutFormation") else None] for e in E]
        open_lv = sorted({lvl_num(y[1]) for y in years if y[2] and lvl_num(y[1])})
        all_lv = sorted({lvl_num(y[1]) for y in years if lvl_num(y[1])} | ({lvl_num(it.get("valeurComNiveau"))} - {None}))
        fees = sorted({y[3] for y in years if y[3]})
        row = {
            "id": key,
            "t": " ".join((it.get("libelleFormation") or "").split()),
            "d": it.get("typeDiplome") or "Other",
            "s": it.get("libelleEtablissement") or "",
            "g": it.get("libelleGroupement") or "",
            "c": city_of(contact.get("adresse")) or city_from_site(it.get("libelleSite")),
            "cat": "English catalogue" if (it.get("libelleCatalogue") or "").startswith("Enseign") or "anglais" in (it.get("libelleCatalogue") or "").lower() else (it.get("libelleCatalogue") or ""),
            "lv": all_lv,
            "ol": open_lv,
            "o": 1 if any(y[2] for y in years) else 0,
            "y": years,
            "par": 1 if (it.get("procedureParallele") or any(e.get("procedureParallele") for e in E)) else 0,
        }
        if ok:
            row["lang"] = LANG.get(g.get("langueEnseignement"), g.get("langueEnseignement") or "")
            dom = " / ".join(x for x in [g.get("domaine"), g.get("sousDomaine")] if isinstance(x, str) and x)
            if dom:
                row["dom"] = dom
            if fees:
                row["fee"] = fees
            dates = [e.get("dateFin") for e in E if not e["ferme"] and e.get("dateFin")]
            if dates:
                row["to"] = max(dates)
            web = re.search(r"https?://\S+|www\.\S+", g.get("UrlInfoSpecifique") or "")
            if web:
                row["web"] = web.group(0).rstrip(".,;)")
            if contact.get("emailContactSite"):
                row["mail"] = contact["emailContactSite"].strip()
            row["eng"] = english_rules(text)
            if FR_LEVEL.search(text):
                row["fr"] = 1
        else:
            row["nd"] = 1  # details could not be downloaded
        rows.append(row)

    # Fill towns missing from the address using the institution's other listings.
    by_inst = {}
    for r in rows:
        if r["c"]:
            by_inst.setdefault(r["s"], Counter())[r["c"]] += 1
    for r in rows:
        if not r["c"] and r["s"] in by_inst:
            r["c"] = by_inst[r["s"]].most_common(1)[0][0]

    meta = {
        "fetched": lst.get("fetched"),
        "built": dt.date.today().isoformat(),
        "count": len(rows),
        "withDetails": sum(1 for r in rows if "nd" not in r),
        "open": sum(r["o"] for r in rows),
    }
    OUT.write_text(
        "// Generated by scripts/build.py from the Études en France catalogue – do not edit by hand.\n"
        "window.META = " + json.dumps(meta, ensure_ascii=False) + ";\n"
        "window.COURSES = " + json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    print(meta)
    print("degree types:", Counter(r["d"] for r in rows).most_common(12))
    print("size MB:", round(OUT.stat().st_size / 1e6, 1))


if __name__ == "__main__":
    build()
