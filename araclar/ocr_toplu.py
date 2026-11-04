#!/usr/bin/env python3
"""Metin katmanı olmayan PDF sayfalarını görüntüye çevirip macOS Vision ile OCR'lar.

Çıktı: kaynak-isleme/ocr/<pdf adı>/<sayfa>.json (kitaptan_cikar.py bu dosyaları kullanır)
Kullanım: python araclar/ocr_toplu.py --kaynak-dizin <klasör> <pdf adı> [--dpi 200]
"""
import argparse, json, os, subprocess, sys, tempfile
from pathlib import Path

import pdfplumber

KOK = Path(__file__).resolve().parent.parent
PDFTOPPM = os.environ.get("PDFTOPPM", "pdftoppm")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaynak-dizin", required=True)
    ap.add_argument("pdfler", nargs="+")
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--parti", type=int, default=12)
    a = ap.parse_args()
    for pdf in a.pdfler:
        isle(a, pdf)
    print("tamam")


def isle(a, pdf_adi):
    kaynak = Path(a.kaynak_dizin) / pdf_adi
    hedef = KOK / "kaynak-isleme" / "ocr" / Path(pdf_adi).stem
    with pdfplumber.open(kaynak) as pdf:
        bos = [i + 1 for i, s in enumerate(pdf.pages) if len((s.extract_text() or "").strip()) < 80]
    if not bos:
        return
    hedef.mkdir(parents=True, exist_ok=True)
    eksik = [n for n in bos if not (hedef / f"{n:04d}.json").exists()]
    print(f"{pdf_adi}: {len(bos)} görüntü sayfası, {len(eksik)} tanesi OCR bekliyor", flush=True)
    with tempfile.TemporaryDirectory() as gecici:
        for i in range(0, len(eksik), a.parti):
            parti = eksik[i:i + a.parti]
            pngler = []
            for n in parti:
                onek = Path(gecici) / f"{n:04d}"
                subprocess.run([PDFTOPPM, "-r", str(a.dpi), "-gray", "-f", str(n), "-l", str(n), "-png", "-singlefile",
                                str(kaynak), str(onek)], check=True)
                pngler.append(str(onek) + ".png")
            subprocess.run(["osascript", "-l", "JavaScript", str(KOK / "araclar" / "ocr_vision.js"), str(hedef)] + pngler,
                           check=False, stderr=subprocess.DEVNULL)
            for p in pngler:
                os.remove(p)
            print(f"  {min(i + a.parti, len(eksik))}/{len(eksik)}", flush=True)


if __name__ == "__main__":
    main()

