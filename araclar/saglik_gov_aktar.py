#!/usr/bin/env python3
"""saglik_gov_tara.py ile indirilen dosyaları içeriğe dönüştürür.

- PDF: kaynak-isleme/segmentler/saglik-gov.json segmentlerini yazar (metin
  kitaptan_cikar.py ile, taranmış sayfalar ocr_toplu.py ile çıkarılır).
- DOCX / DOC: doğrudan icerik/<tür>/ altına Markdown yazar (DOC önce LibreOffice ile DOCX'e çevrilir).
- Diğerleri: kaynak-isleme/katalog/saglik-gov.json içinde künye + bağlantı olarak kalır.

Kullanım: python araclar/saglik_gov_aktar.py
"""
import json, os, re, subprocess, sys, unicodedata
from pathlib import Path

import docx
import pdfplumber

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "araclar"))
from docx_aktar import paragraf_md  # noqa: E402

INDIRILEN = KOK / "kaynak-isleme" / "indirilen"
SOFFICE = os.environ.get("SOFFICE", "soffice")


def sade_id(s):
    s = unicodedata.normalize("NFKD", s.lower().replace("ı", "i"))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:70].strip("-")


def kunye(o, tur):
    baslik = o["baslik"].strip()
    veri = {"tur": tur}
    m = re.match(r"^Tarih:\s*(\d{2})\.(\d{2})\.(\d{4})\s*/\s*Sayı:\s*(\d+)\s*(.*)$", baslik)
    if m:
        veri.update(tarih=f"{m.group(3)}-{m.group(2)}-{m.group(1)}", sayi=m.group(4))
        baslik = m.group(5)
    m = re.search(r"\((\d{4})\s*/\s*(\d+)\)\s*$", baslik)
    if m and tur == "genelge":
        veri["sayi"] = f"{m.group(1)}/{m.group(2)}"
    if baslik.endswith("..."):
        veri["not"] = "Başlık kaynak listede kısaltılmış."
    veri.update(id=f"sbg-{o['trid']}-{sade_id(baslik)}", baslik=baslik.rstrip(". "), birim=o.get("birim", ""),
                kaynak="T.C. Sağlık Bakanlığı internet sitesi (saglik.gov.tr)", kaynak_url=o["url"], durum="yürürlükte")
    return {k: v for k, v in veri.items() if v}


def docx_yaz(yol, veri):
    belge = docx.Document(yol)
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
    if sum(len(b) for b in bloklar) < 200:
        return False
    on = ["---"] + [f"{a}: {json.dumps(b, ensure_ascii=False)}" for a, b in veri.items()] + ["---"]
    hedef = KOK / "icerik" / veri["tur"] / f"{veri['id']}.md"
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_text("\n".join(on) + "\n\n" + "\n\n".join(bloklar) + "\n", encoding="utf-8")
    return True


def main():
    segmentler, katalog = [], []
    for dizin in sorted((KOK / "kaynak-isleme" / "saglik-gov").glob("*.json")):
        tur = dizin.stem
        for o in json.loads(dizin.read_text(encoding="utf-8")):
            veri = kunye(o, tur)
            dosya = INDIRILEN / tur / o.get("dosya", "-")
            tip = o.get("tip")
            tamam = False
            if o.get("resmi_url"):
                veri["kaynak_url"] = o["resmi_url"]
            ekler = [e for e in o.get("ekler", []) if (INDIRILEN / tur / e["dosya"]).exists()]
            pdf_ekler = [e for e in ekler if e["tip"] == "pdf"]
            word_ekler = [e for e in ekler if e["tip"] in ("docx", "doc")]
            if pdf_ekler:
                parcalar = []
                for e in sorted(pdf_ekler, key=lambda e: not e["ustyazi"]):
                    try:
                        with pdfplumber.open(INDIRILEN / tur / e["dosya"]) as pdf:
                            parcalar.append({"kaynak_pdf": f"{tur}/{e['dosya']}", "pdf_baslangic": 1, "pdf_bitis": len(pdf.pages)})
                    except Exception as hata:
                        print("PDF açılamadı:", e["dosya"], hata)
                if parcalar:
                    segmentler.append({**veri, "parcalar": parcalar})
                    tamam = True
            elif word_ekler:
                e = word_ekler[0]
                tip, dosya = e["tip"], INDIRILEN / tur / e["dosya"]
            if tamam:
                pass
            elif tip == "pdf" and dosya.exists():
                try:
                    with pdfplumber.open(dosya) as pdf:
                        n = len(pdf.pages)
                    segmentler.append({**veri, "kaynak_pdf": f"{tur}/{dosya.name}", "pdf_baslangic": 1, "pdf_bitis": n})
                    tamam = True
                except Exception as hata:
                    print("PDF açılamadı:", dosya.name, hata)
            elif tip == "doc" and dosya.exists():
                cikti = dosya.with_suffix(".docx")
                if not cikti.exists():
                    subprocess.run([SOFFICE, "--headless", "--convert-to", "docx", "--outdir", str(dosya.parent), str(dosya)],
                                   capture_output=True, timeout=180)
                if cikti.exists():
                    tamam = docx_yaz(cikti, veri)
            elif tip == "docx" and dosya.exists():
                try:
                    tamam = docx_yaz(dosya, veri)
                except Exception as hata:
                    print("DOCX okunamadı:", dosya.name, hata)
            if not tamam:
                katalog.append(veri)
    (KOK / "kaynak-isleme" / "segmentler" / "saglik-gov.json").write_text(
        json.dumps(segmentler, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (KOK / "kaynak-isleme" / "katalog" / "saglik-gov.json").write_text(
        json.dumps(katalog, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(segmentler)} PDF segmenti, {len(katalog)} yalnızca künye kaydı")


if __name__ == "__main__":
    main()

