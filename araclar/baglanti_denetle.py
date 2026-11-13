#!/usr/bin/env python3
"""Sitedeki kaynak bağlantılarını dener; açılmayanları ve "Sayfa Bulunmadı" dönenleri raporlar.

Ayda bir GitHub Actions ile çalışır (bkz. .github/workflows/baglanti-denetimi.yml) ve
sorun varsa depoda bir konu (issue) açar. Elle: python araclar/baglanti_denetle.py
"""
import concurrent.futures as cf, html, os, re, sys, urllib.error, urllib.parse, urllib.request
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (CanliSaglikMevzuati baglanti denetimi)"}


def topla():
    adresler = {}
    for md in sorted((KOK / "icerik").glob("*/*.md")):
        bas = md.read_text(encoding="utf-8").split("---\n")[1]
        m = re.search(r'^kaynak_url: "(.*)"', bas, re.M)
        if m:
            adresler.setdefault(m.group(1).split("#")[0], []).append(f"{md.parent.name}/{md.stem}")
    return adresler


def dene(u):
    try:
        q = urllib.parse.quote(u, safe=":/?&=%#+,;@()~!*'")
        with urllib.request.urlopen(urllib.request.Request(q, headers=UA), timeout=45) as r:
            govde = r.read(60000).decode("utf-8", "ignore") if "html" in r.headers.get("Content-Type", "") else ""
        m = re.search(r"<title[^>]*>(.*?)</title>", govde, re.S | re.I)
        baslik = html.unescape(m.group(1)).strip() if m else ""
        if re.search(r"Sayfa Bulun(a)?madı|404|Not Found", baslik, re.I):
            return u, "sayfa bulunamadı"
        if "mevzuat.gov.tr/mevzuat?" in u:  # dış sayfa hep açılır; asıl metin çerçevesine bakılır
            p = dict(x.split("=") for x in u.split("?")[1].split("&"))
            c = (f"https://www.mevzuat.gov.tr/anasayfa/MevzuatFihristDetayIframe?MevzuatTur={p['MevzuatTur']}"
                 f"&MevzuatNo={p['MevzuatNo']}&MevzuatTertip={p['MevzuatTertip']}")
            with urllib.request.urlopen(urllib.request.Request(c, headers=UA), timeout=60) as r:
                if "MEVZUAT BİLGİ SİSTEMİ" in re.sub(r"<[^>]+>", " ", r.read(20000).decode("utf-8", "ignore"))[:600]:
                    return u, "mevzuat.gov.tr metni boş"
        return u, ""
    except urllib.error.HTTPError as h:
        return u, f"HTTP {h.code}"
    except Exception as h:
        return u, f"açılmadı ({str(h)[:60]})"


def main():
    adresler = topla()
    with cf.ThreadPoolExecutor(6) as ex:
        sonuc = [(u, s) for u, s in ex.map(dene, adresler) if s]
    satirlar = [f"- {s}: {u} — " + ", " .join(adresler[u][:3]) for u, s in sorted(sonuc, key=lambda x: x[1])]
    rapor = f"{len(adresler)} bağlantı denendi, {len(sonuc)} sorun bulundu.\n\n" + "\n".join(satirlar) + "\n"
    print(rapor)
    (KOK / "baglanti-raporu.md").write_text(rapor, encoding="utf-8")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"sorun={len(sonuc)}\n")


if __name__ == "__main__":
    main()
