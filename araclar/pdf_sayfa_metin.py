#!/usr/bin/env python3
"""Metin katmanlı PDF'i sayfa başına .txt dosyalarına çevirir; paragraf başlarını (girinti / satır aralığı)
boş satırla ayırır. ocr_ilk_metin.py girdisi üretir. pdfplumber gerektirir.
Kullanım: python pdf_sayfa_metin.py <pdf> <çıktı_klasörü>"""
import statistics, subprocess, sys, tempfile
from pathlib import Path
import pdfplumber
import pypdfium2


def sayfa(p):
    satirlar = {}
    for w in p.extract_words(keep_blank_chars=False, use_text_flow=True, extra_attrs=["size"]):
        satirlar.setdefault(round(w["top"] / 3), []).append(w)
    sat = []
    for k in sorted(satirlar):
        ws = sorted(satirlar[k], key=lambda w: w["x0"])
        sat.append((ws[0]["top"], ws[0]["x0"], ws[-1]["x1"], " ".join(w["text"] for w in ws)))
    if not sat:
        return ""
    sol = min(x for _, x, _, _ in sat)
    sag = max(x for _, _, x, _ in sat)
    araliklar = [b[0] - a[0] for a, b in zip(sat, sat[1:]) if b[0] > a[0]]
    tipik = statistics.median(araliklar) if araliklar else 12
    out, onceki = [], None
    for top, x0, x1, t in sat:
        yeni = onceki is None or (top - onceki[0]) > tipik * 1.45 or x0 > sol + 12 \
            or (onceki[2] < sag - 40 and onceki[3].rstrip()[-1:] in ".:;")
        if yeni and out:
            out.append("")
        out.append(t)
        onceki = (top, x0, x1, t)
    return "\n".join(out)


def main():
    pdf, cikti = sys.argv[1], Path(sys.argv[2])
    cikti.mkdir(parents=True, exist_ok=True)
    gor = pypdfium2.PdfDocument(pdf)
    with pdfplumber.open(pdf) as d:
        for i, p in enumerate(d.pages, 1):
            yol = cikti / f"p{i:03d}.txt"
            if yol.exists() and yol.stat().st_size:
                continue
            t = sayfa(p)
            if len(t.strip()) < 40:  # taranmış sayfa: Tesseract (Türkçe)
                with tempfile.NamedTemporaryFile(suffix=".png") as png:
                    gor[i - 1].render(scale=4).to_pil().convert("L").save(png.name)
                    t = subprocess.run(["/opt/homebrew/bin/tesseract", png.name, "-", "-l", "tur", "--psm", "1"],
                                       capture_output=True, text=True).stdout
            yol.write_text(t, encoding="utf-8")
    print(pdf, len(list(cikti.glob("p*.txt"))))


if __name__ == "__main__":
    main()
