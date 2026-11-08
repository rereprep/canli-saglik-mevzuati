#!/usr/bin/env python3
"""Kanun, KHK ve Cumhurbaşkanlığı kararnamelerinin mevzuat.gov.tr'deki
"... YÜRÜRLÜĞE GİRİŞ TARİHLERİNİ GÖSTERİR LİSTE/TABLO" tablolarını toplar.
Çıktı: kaynak-isleme/mevzuat-gov/degisiklik-listeleri.json  {kayıt_id: {"baslik": .., "satirlar": [[..]], "url": ..}}
Tablosu olmayanlar için site_uret.py metindeki değişiklik notlarından liste üretir.
Kullanım: python araclar/degisiklik_listesi.py [--yeniden]
"""
import html, json, re, sys, time, urllib.request
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "araclar"))
from site_uret import belgeleri_oku  # noqa: E402

CIKTI = KOK / "kaynak-isleme" / "mevzuat-gov" / "degisiklik-listeleri.json"
ESLESME = KOK / "kaynak-isleme" / "mevzuat-gov" / "eslesme.json"
TUR_NO = {"kanun": 1, "khk": 4, "cbk": 19}
UA = "Mozilla/5.0 (CanliSaglikMevzuati)"


def al(url):
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
        except Exception:
            time.sleep(3 * (i + 1))
    return ""


def hucre(c):
    c = re.sub(r"<br\s*/?>", " ", c)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", c))).strip()


def satir_oku(tb):
    """Tablodaki satırları birleşik hücreleri (colspan/rowspan) açarak okur."""
    sonuc, bekleyen = [], {}  # bekleyen: sütun -> (metin, kalan satır)
    for r in re.findall(r"<tr.*?</tr>", tb, re.S):
        satir, sutun = [], 0
        for c in re.finditer(r"<t[dh]([^>]*)>(.*?)</t[dh]>", r, re.S):
            while sutun in bekleyen:
                metin, kalan = bekleyen[sutun]
                satir.append(None)  # üstteki birleşik hücrenin devamı
                bekleyen[sutun] = (metin, kalan - 1)
                if kalan - 1 <= 0:
                    del bekleyen[sutun]
                sutun += 1
            cs = int((re.search(r'colspan="?(\d+)', c[1]) or [0, 1])[1])
            rs = int((re.search(r'rowspan="?(\d+)', c[1]) or [0, 1])[1])
            metin = hucre(c[2])
            for k in range(cs):
                satir.append(metin if k == 0 else "")
                if rs > 1:
                    bekleyen[sutun] = (metin, rs - 1)
                sutun += 1
        while sutun in bekleyen:
            metin, kalan = bekleyen[sutun]
            satir.append(None)
            bekleyen[sutun] = (metin, kalan - 1)
            if kalan - 1 <= 0:
                del bekleyen[sutun]
            sutun += 1
        if any(satir):
            sonuc.append(satir)
    return sonuc


def basliklari_birlestir(satirlar):
    """İki satırlı sütun başlığını tek satıra indirir: üst başlık + alt başlık."""
    if len(satirlar) >= 2 and any(h is None for h in satirlar[1]) and not re.search(r"\d", "".join(h or "" for h in satirlar[1])):
        ust, alt = satirlar[0], satirlar[1]
        bas, son = [], ""
        for i in range(max(len(ust), len(alt))):
            u = ust[i] if i < len(ust) else ""
            a = alt[i] if i < len(alt) else None
            son = u if u else son
            bas.append((son + " – " + a) if a else (u or son))
        satirlar = [bas] + satirlar[2:]
    return [[h or "" for h in r] for r in satirlar]


def tablo_cikar(t):
    tablolar = list(re.finditer(r"<table.*?</table>", t, re.S))
    bas, baslik = None, ""
    for n, tb in enumerate(tablolar):
        once = hucre(t[max(0, tb.start() - 3000):tb.start()])
        m = None
        for m in re.finditer(r"(?<![\dA-Za-zÇĞİÖŞÜçğıöşü])(?:\d+\s+SAYILI|[A-ZÇĞİÖŞÜ]{3})[^.:;]{0,300}?GÖSTERİR (?:LİSTE|TABLO|CETVEL)", once):
            pass
        if m:
            bas, baslik = n, m.group(0).strip()
    if bas is None:
        return None
    satirlar = []
    for tb in tablolar[bas:]:
        satirlar += satir_oku(tb.group(0))
    satirlar = basliklari_birlestir(satirlar)
    return {"baslik": baslik, "satirlar": satirlar} if satirlar else None


def hedefler():
    es = json.loads(ESLESME.read_text(encoding="utf-8")) if ESLESME.exists() else {}
    for b in belgeleri_oku().values():
        if b["tur"] not in TUR_NO or not b.get("tam_metin"):
            continue
        idler = [b["id"]] + [i for _, i in b.get("eski_kimlikler", [])]
        aday = []
        for i in idler:
            e = es.get(i)
            if e and e.get("tur") in TUR_NO.values():
                aday.append((e["tur"], e["no"], e.get("tertip", "5")))
        for u in [b.get("kaynak_url", "")] + b.get("diger_url", []):
            m = re.search(r"MevzuatNo=(\d+)&MevzuatTur=(\d+)&MevzuatTertip=(\d+)", u or "")
            if m:
                aday.append((int(m[2]), m[1], m[3]))
        no = re.sub(r"\D", "", str(b.get("sayi", "")))
        if no:
            aday += [(TUR_NO[b["tur"]], no, t) for t in ("5", "4", "3")]
            if b["tur"] == "khk":  # KHK'yi değiştirerek kabul eden kanunlar
                aday += [(1, no, t) for t in ("5", "4", "3")]
        yield b, list(dict.fromkeys(aday))


def main():
    eski = {} if "--yeniden" in sys.argv or not CIKTI.exists() else json.loads(CIKTI.read_text(encoding="utf-8"))
    sonuc = dict(eski)
    for b, adaylar in hedefler():
        if sonuc.get(b["id"], {}).get("satirlar"):
            continue
        for tur, no, tertip in adaylar:
            url = f"https://www.mevzuat.gov.tr/anasayfa/MevzuatFihristDetayIframe?MevzuatTur={tur}&MevzuatNo={no}&MevzuatTertip={tertip}"
            t = al(url)
            time.sleep(0.6)
            if len(t) < 3000:
                continue
            tb = tablo_cikar(t)
            sonuc[b["id"]] = dict(tb, url=url.replace("anasayfa/MevzuatFihristDetayIframe", "mevzuat")) if tb else {"yok": True, "url": url}
            print(b["id"][:60], "->", (len(tb["satirlar"]) if tb else "tablo yok"), flush=True)
            break
        else:
            print(b["id"][:60], "-> bulunamadı", flush=True)
    CIKTI.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(sum(1 for v in sonuc.values() if v.get("satirlar")), "tablo")


if __name__ == "__main__":
    main()
