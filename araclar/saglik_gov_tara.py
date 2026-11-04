#!/usr/bin/env python3
"""saglik.gov.tr mevzuat sayfalarındaki yönerge ve genelgeleri indirir.

1) Liste sayfasındaki birim başlıklarını ve belge bağlantılarını okur.
2) Her belgeyi (PDF/Word) kaynak-isleme/indirilen/<tür>/ altına indirir.
3) kaynak-isleme/saglik-gov/<tür>.json dizinini yazar; metin çıkarma için
   araclar/saglik_gov_aktar.py kullanılır.

Kullanım: python araclar/saglik_gov_tara.py [--tur yonerge genelge]
"""
import argparse, html, json, re, sys, time, urllib.request
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
# Bakanlık sitesindeki mevzuat sayfaları tüm site ağacını içerir; bölüm başlıklarından tür belirlenir.
LISTE_URL = "https://www.saglik.gov.tr/TR-11186/yonergeler.html"
BOLUMLER = {"Kanunlar": "kanun", "Yönetmelikler": "yonetmelik", "Genelgeler": "genelge",
            "Yönergeler": "yonerge", "Tüzükler": "tuzuk"}
LISTELER = {"kanun": 1, "yonetmelik": 1, "genelge": 1, "yonerge": 1, "tuzuk": 1, "teblig": 1}
BIRIM = re.compile(r"(Genel Müdürlüğü|Başkanlığı|Kurumu|Birimi|Müsteşarlık|Daire Başkanlığı)$")
UA = {"User-Agent": "Mozilla/5.0 (CanliSaglikMevzuati)"}
OGE = re.compile(r'<li>\s*<a id="(\d+)" href="(/TR-\d+/[^"]+)" target="([^"]*)"\s*>\s*(.*?)\s*</a>\s*</li>(\s*<ul class="siteagac)?', re.S)


def getir(url, deneme=3):
    import concurrent.futures

    def _al():
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
            return r.read(), r.headers.get("Content-Type", ""), r.headers.get("Content-Disposition", "")

    for i in range(deneme):
        havuz = concurrent.futures.ThreadPoolExecutor(1)
        try:
            return havuz.submit(_al).result(timeout=90)  # yavaş akan yanıtlarda toplam süre sınırı
        except Exception as hata:
            if i == deneme - 1:
                raise
            time.sleep(3 * (i + 1))
        finally:
            havuz.shutdown(wait=False)


def liste_oku(tur):
    ham, _, _ = getir(LISTE_URL)
    sayfa = ham.decode("utf-8", "replace")
    bas = sayfa.find('class="siteagac')
    sayfa = sayfa[max(0, bas - 4000):]
    birim, bolum, ogeler, gorulen = "", None, [], set()
    for m in OGE.finditer(sayfa):
        trid, href, hedef, metin, alt_liste = m.groups()
        baslik = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", metin)).split())
        if alt_liste:
            if baslik in BOLUMLER:
                bolum, birim = BOLUMLER[baslik], ""
            elif baslik.upper().startswith("TEBLİĞLER"):
                bolum, birim = "teblig", baslik.split("-", 1)[-1].strip()
            elif bolum and BIRIM.search(baslik):
                birim = baslik
            else:
                bolum = None
            continue
        if bolum != tur or trid in gorulen:
            continue
        gorulen.add(trid)
        ogeler.append({"trid": trid, "baslik": baslik, "birim": birim, "url": "https://www.saglik.gov.tr" + href})
    return ogeler


def uzanti(icerik, tip, ad):
    if icerik[:4] == b"%PDF":
        return "pdf"
    if icerik[:2] == b"PK":
        return "docx" if b"word/" in icerik[:4000] or "word" in tip else "zip"
    if icerik[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return "doc"
    if b"<html" in icerik[:2000].lower():
        return "html"
    m = re.search(r"\.(\w{2,4})\"?$", ad or "")
    return m.group(1).lower() if m else "bin"


DOSYA_BAG = re.compile(r'href="((?:https?://[^"]*saglik\.gov\.tr)?/?[^"]*?(?:Eklenti/[^"]+|\.(?:pdf|PDF|docx?|DOCX?)))"')


def ekleri_izle(tur):
    dizin_yolu = KOK / "kaynak-isleme" / "saglik-gov" / f"{tur}.json"
    if not dizin_yolu.exists():
        return
    ogeler = json.loads(dizin_yolu.read_text(encoding="utf-8"))
    klasor = KOK / "kaynak-isleme" / "indirilen" / tur
    import concurrent.futures
    isler = [o for o in ogeler if o.get("tip") == "html" and "ekler" not in o]
    print(f"{tur}: {len(isler)} ara sayfa izlenecek", flush=True)
    with concurrent.futures.ThreadPoolExecutor(4) as havuz:
        for i, _ in enumerate(havuz.map(lambda o: ek_indir(o, klasor), isler)):
            if (i + 1) % 20 == 0:
                print(f"  {tur}: {i + 1}/{len(isler)}", flush=True)
                dizin_yolu.write_text(json.dumps(ogeler, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    dizin_yolu.write_text(json.dumps(ogeler, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{tur}: ekler tamam", flush=True)


def ek_indir(o, klasor):
    if True:
        sayfa = (klasor / o["dosya"]).read_text(encoding="utf-8", errors="replace")
        baglar = []
        for b in DOSYA_BAG.findall(sayfa):
            b = html.unescape(b)
            b = b if b.startswith("http") else urllib.request.urljoin("https://www.saglik.gov.tr/", b)
            if b not in baglar:
                baglar.append(b)
        if not baglar:
            m = re.search(r'href="(https?://(?:www\.)?mevzuat\.gov\.tr/[^"]+)"', sayfa)
            if m:
                o["resmi_url"] = html.unescape(m.group(1))
            o["ekler"] = []
            return
        ekler = []
        for j, b in enumerate(baglar[:6]):
            onceki = sorted(klasor.glob(f"{o['trid']}-ek{j + 1}.*"))
            if onceki:
                ekler.append({"dosya": onceki[0].name, "tip": onceki[0].suffix[1:], "url": b,
                              "ustyazi": "ustyazi" in b.lower() or "ust-yazi" in b.lower()})
                continue
            try:
                icerik, tip, ad = getir(b)
            except Exception as hata:
                print(f"  ! {o['trid']} eki indirilemedi: {hata}", flush=True)
                continue
            uz = uzanti(icerik, tip, ad)
            dosya = f"{o['trid']}-ek{j + 1}.{uz}"
            (klasor / dosya).write_bytes(icerik)
            ekler.append({"dosya": dosya, "tip": uz, "url": b, "ustyazi": "ustyazi" in b.lower() or "ust-yazi" in b.lower()})
            time.sleep(0.3)
        o["ekler"] = ekler


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tur", nargs="*", default=list(LISTELER))
    ap.add_argument("--ekleri-izle", action="store_true",
                    help="Ara sayfa (HTML) olarak inen kayıtlardaki asıl PDF/Word bağlantılarını indir")
    a = ap.parse_args()
    if a.ekleri_izle:
        for tur in a.tur:
            ekleri_izle(tur)
        return
    for tur in a.tur:
        ogeler = liste_oku(tur)
        print(f"{tur}: {len(ogeler)} bağlantı", flush=True)
        klasor = KOK / "kaynak-isleme" / "indirilen" / tur
        klasor.mkdir(parents=True, exist_ok=True)
        dizin_yolu = KOK / "kaynak-isleme" / "saglik-gov" / f"{tur}.json"
        dizin_yolu.parent.mkdir(parents=True, exist_ok=True)
        eski = {o["trid"]: o for o in json.loads(dizin_yolu.read_text())} if dizin_yolu.exists() else {}
        for i, o in enumerate(ogeler):
            if o["trid"] in eski and (klasor / eski[o["trid"]].get("dosya", "-")).exists():
                o.update({k: v for k, v in eski[o["trid"]].items() if k in ("dosya", "tip")})
                continue
            onceki = sorted(klasor.glob(o["trid"] + ".*"))
            if onceki:
                o["dosya"], o["tip"] = onceki[0].name, onceki[0].suffix[1:]
                continue
            try:
                icerik, tip, ad = getir(o["url"])
            except Exception as hata:
                print(f"  ! {o['trid']} indirilemedi: {hata}", flush=True)
                o["tip"] = "hata"
                continue
            uz = uzanti(icerik, tip, ad)
            o["tip"] = uz
            o["dosya"] = f"{o['trid']}.{uz}"
            (klasor / o["dosya"]).write_bytes(icerik)
            if (i + 1) % 25 == 0:
                print(f"  {i + 1}/{len(ogeler)}", flush=True)
                dizin_yolu.write_text(json.dumps(ogeler, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            time.sleep(0.3)
        dizin_yolu.write_text(json.dumps(ogeler, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{tur}: tamam", flush=True)


if __name__ == "__main__":
    main()

