#!/usr/bin/env python3
"""Resmî Gazete (ve saglik.gov.tr HTML) kaynaklı metinleri güncel html_md ile yeniden üretir.
Künye korunur; elle/ajanla düzeltilmiş (duzeltildi: true) dosyalara dokunulmaz.
Kullanım: python araclar/rg_yeniden.py [--hepsi]"""
import re, sys, time
from pathlib import Path
KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "araclar"))
from kaynaktan_aktar import getir, coz, capa_bolumu  # noqa: E402
from mevzuat_gov_aktar import html_md  # noqa: E402


def main():
    yazilan = 0
    for f in sorted((KOK / "icerik").glob("*/*.md")):
        t = f.read_text(encoding="utf-8")
        son = t.index("\n---\n", 4)
        on, govde = t[:son + 5], t[son + 5:]
        if "\nduzeltildi: true" in on:
            continue
        m = re.search(r'^kaynak_url: "([^"]+)"', on, re.M)
        if not m:
            continue
        url = m.group(1)
        rg = "resmigazete.gov.tr" in url and re.search(r"\.htm(#\w+)?$", url)
        bozuk = "| Resmî Gazete |" in govde or len(re.findall(r"(?<=\w) [ÇĞİÖŞÜçğıöşü] (?=\w)", govde)) > 20
        if not (rg or bozuk) or not bozuk and "--hepsi" not in sys.argv:
            continue
        try:
            sayfa = coz(getir(url))
        except Exception as hata:
            print("!", f.name, hata)
            continue
        if "#" in url:
            sayfa = capa_bolumu(sayfa, url.rsplit("#", 1)[1])
        elif "saglik.gov.tr" in url:
            bas = sayfa.find('class="pages_content')
            if bas >= 0:
                bitis = sayfa.find('class="page_sub_links_content', bas)
                sayfa = sayfa[bas:bitis if bitis > 0 else bas + 200000]
                sayfa = sayfa[sayfa.find(">") + 1:]
        yeni = html_md(sayfa)
        if len(yeni) < 0.6 * len(govde.strip()):
            print("? kısa çıktı, atlandı:", f.name, len(govde), len(yeni))
            continue
        f.write_text(on + "\n" + yeni, encoding="utf-8")
        yazilan += 1
        print("yazıldı", f.name, len(govde), "->", len(yeni), flush=True)
        time.sleep(0.5)
    print(yazilan, "dosya yenilendi")


if __name__ == "__main__":
    main()
