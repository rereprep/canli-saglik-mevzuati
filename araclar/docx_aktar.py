#!/usr/bin/env python3
"""Yönergeler klasöründeki Word (.docx) yönerge metinlerini icerik/yonerge/ altına aktarır.

Üst yazılar ve taslak (düzenlenmiş) kopyalar atlanır. Künye bilgileri aynı klasördeki
Excel listelerinden alınır.
Kullanım: python araclar/docx_aktar.py --kaynak-dizin "<Yönergeler klasörü>"
"""
import argparse, datetime as dt, json, re, unicodedata
from pathlib import Path

import docx
import openpyxl

KOK = Path(__file__).resolve().parent.parent


def sade(s):
    s = unicodedata.normalize("NFC", s or "").casefold().replace("i̇", "i")
    return re.sub(r"[^0-9a-z]+", " ", s.translate(str.maketrans("çğıöşüâîû", "cgiosuaiu"))).strip()


def kimlik(s):
    return "dx-" + sade(s).replace(" ", "-")[:90]


def tarih(v):
    if isinstance(v, dt.datetime):
        return v.date().isoformat()
    if isinstance(v, (int, float)) and 20000 < v < 60000:
        return (dt.date(1899, 12, 30) + dt.timedelta(days=int(v))).isoformat()
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", str(v or ""))
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else ""


def kunyeler(dizin):
    sonuc = {}
    for x in sorted(Path(dizin).glob("*.xlsx")):
        wb = openpyxl.load_workbook(x, read_only=True)
        for ws in wb.worksheets:
            satirlar = list(ws.iter_rows(values_only=True))
            if not satirlar:
                continue
            bas = [sade(str(h or "")) for h in satirlar[0]]
            for r in satirlar[1:]:
                k = dict(zip(bas, r))
                ad = k.get("yonerge adi")
                if not ad:
                    continue
                kayit = sonuc.setdefault(sade(ad), {})
                for alan, kaynak in (("tarih", "tarih"), ("sayi", "sayi"), ("birim", "birim"), ("konu", "konu")):
                    v = k.get(kaynak)
                    if v and not kayit.get(alan):
                        kayit[alan] = tarih(v) if alan == "tarih" else str(v).strip()
                for anahtar in ("resmi link", "link"):
                    v = k.get(anahtar)
                    if v and str(v).startswith("http") and not kayit.get("kaynak_url") and "TR-11186" not in str(v):
                        kayit["kaynak_url"] = str(v).strip()
    return sonuc


def paragraf_md(p):
    metin = " ".join(p.text.split())
    if not metin:
        return None
    m = re.match(r"^((?:GEÇİCİ |Geçici |EK |Ek )?(?:MADDE|Madde)\s*\d+[/A-Za-z]*)\s*[-–—:]\s*", metin)
    if m:
        return f"**{m.group(1)} –** {metin[m.end():]}"
    harfler = [c for c in metin if c.isalpha()]
    if harfler and len(metin) < 140 and sum(c.isupper() for c in harfler) / len(harfler) > 0.9:
        return "### " + metin
    if p.style.name.lower().startswith("heading") or (len(metin) < 100 and all(r.bold for r in p.runs if r.text.strip()) and not metin.endswith(".")):
        return "#### " + metin
    return metin


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaynak-dizin", required=True)
    a = ap.parse_args()
    dizin = Path(a.kaynak_dizin)
    kunye = kunyeler(dizin)
    yazilan = 0
    for klasor in sorted(p for p in dizin.iterdir() if p.is_dir()):
        aday = klasor / (klasor.name + ".docx")
        if not aday.exists():
            continue
        belge = docx.Document(aday)
        bloklar = [b for b in (paragraf_md(p) for p in belge.paragraphs) if b]
        for t in belge.tables:
            for satir in t.rows:
                hucreler = []
                for c in satir.cells:
                    x = " ".join(c.text.split())
                    if not hucreler or hucreler[-1] != x:
                        hucreler.append(x)
                if any(hucreler):
                    bloklar.append(" | ".join(hucreler))
        k = kunye.get(sade(klasor.name), {})
        ad = unicodedata.normalize("NFC", klasor.name)
        veri = {"id": kimlik(ad), "baslik": ad, "tur": "yonerge"}
        veri.update({a: b for a, b in k.items() if b})
        veri["kaynak"] = "Sağlık Bakanlığı yönerge metni (Word)"
        veri["durum"] = "yürürlükte"
        on = ["---"] + [f"{a}: {json.dumps(b, ensure_ascii=False)}" for a, b in veri.items()] + ["---"]
        hedef = KOK / "icerik" / "yonerge" / f"{veri['id']}.md"
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_text("\n".join(on) + "\n\n" + "\n\n".join(bloklar) + "\n", encoding="utf-8")
        yazilan += 1
        print(" ", klasor.name, len(bloklar), "blok")
    print(yazilan, "yönerge aktarıldı")


if __name__ == "__main__":
    main()

