#!/usr/bin/env python3
"""Kanun/KHK için sürüm indeksi: ilk RG metni + metindeki "(Değişik: g/a/yyyy-6514/43 md.)" notlarındaki değiştiren
kanunların RG metinleri. kaynak-isleme/surum/indeks.json'a {deg:[{t,url,ad,kanun,maddeler}]} olarak ekler.
Kullanım: python araclar/surum_kanun.py [--yil 1997]"""
import datetime as dt, json, re, sys
from pathlib import Path
KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "araclar"))
from surum_indir import fihrist, getir, coz, sade, fihrist_url  # noqa: E402

NOT = re.compile(r"\((?:Değişik|Ek|Mülga|Yeniden düzenleme)[^():]*:\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*[-–]\s*(KHK[-/–\s]*)?(\d{3,4})\s*/\s*(\d+)\s*md")


def gunler(bas, n):
    d = dt.date.fromisoformat(bas)
    for i in range(n):
        yield (d + dt.timedelta(days=i)).isoformat()


def rg_bul(no, khk, kabul, gun=60):
    """Kabul tarihinden sonraki RG fihristlerinde numarası 'no' olan kanunu/KHK'yi arar."""
    for t in gunler(kabul, gun):
        try:
            baglar = fihrist(t)
        except Exception:
            continue
        for u, m in baglar:
            mm = m.strip("—–- ")
            if re.match(rf"^{no}\b", mm) and ("Kanun" in mm or "Kararname" in mm or khk):
                return t, u, mm
    return None


def main():
    yil = int(sys.argv[sys.argv.index("--yil") + 1]) if "--yil" in sys.argv else 1997
    indeks_yol = KOK / "kaynak-isleme" / "surum" / "indeks.json"
    indeks = json.loads(indeks_yol.read_text())
    for f in sorted((KOK / "icerik" / "kanun").glob("*.md")):
        s = f.read_text(encoding="utf-8")
        fm = s[:2000]
        if "mevzuat.gov.tr" not in fm:
            continue
        rg = re.search(r'^rg_tarih: "(\d{4}-\d{2}-\d{2})"', fm, re.M)
        no = re.search(r'^sayi: "(\d+)"', fm, re.M)
        kimlik = re.search(r'^id: "([^"]+)"', fm, re.M).group(1)
        baslik = re.search(r'^baslik: "([^"]+)"', fm, re.M).group(1)
        if not rg or not no or int(rg.group(1)[:4]) < yil:
            continue
        kay = indeks.get(kimlik) or {"baslik": baslik, "tur": "kanun", "no": no.group(1), "ilk": {"t": rg.group(1), "sayi": ""}, "deg": []}
        if not kay["ilk"].get("url"):
            for t in gunler(rg.group(1), 1):
                for u, m in fihrist(t):
                    if re.match(rf"^\W*{no.group(1)}\b", m):
                        kay["ilk"].update(url=u, ad=m)
        yur = {}
        for c0, son in re.findall(r"^\|\s*([^|]{1,40}?)\s*\|.*\|\s*([^|]*?)\s*\|\s*$", s, re.M):
            k = re.match(r"^(KHK\s*/\s*)?(\d{3,4})$", c0.strip())
            t = re.findall(r"(\d{1,2})/(\d{1,2})/(\d{4})", son)
            if k and len(t) == 1:
                yur[("KHK-" if k.group(1) else "") + k.group(2)] = f"{t[0][2]}-{int(t[0][1]):02d}-{int(t[0][0]):02d}"
        gruplar = {}
        for g, a, y, khk, n, md in NOT.findall(s):
            kabul = f"{y}-{int(a):02d}-{int(g):02d}"
            k = ("KHK-" if khk else "") + n
            gruplar.setdefault(k, {"kabul": kabul, "khk": bool(khk), "no": n, "maddeler": set()})["maddeler"].add(int(md))
        var = {d.get("kanun") for d in kay["deg"]}
        for k, v in sorted(gruplar.items(), key=lambda x: x[1]["kabul"]):
            if k in var or v["kabul"] < rg.group(1):
                continue
            r = None
            if yur.get(k, "") >= v["kabul"]:
                r = rg_bul(v["no"], v["khk"], yur[k], 1)
            r = r or rg_bul(v["no"], v["khk"], v["kabul"], 3 if v["khk"] else 60)
            d = {"kanun": k, "kabul": v["kabul"], "maddeler": sorted(v["maddeler"]), "t": r[0] if r else v["kabul"], "sayi": ""}
            if r:
                d.update(url=r[1], ad=r[2])
                getir(r[1])
            kay["deg"].append(d)
        kay["deg"].sort(key=lambda d: d["t"])
        indeks[kimlik] = kay
        indeks_yol.write_text(json.dumps(indeks, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{sum(1 for d in kay['deg'] if d.get('url'))}/{len(kay['deg'])} ilk={'+' if kay['ilk'].get('url') else '-'} {baslik[:60]}", flush=True)


if __name__ == "__main__":
    main()
