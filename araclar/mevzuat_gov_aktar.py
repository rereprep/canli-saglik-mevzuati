#!/usr/bin/env python3
"""Tam metni olmayan kanun, KHK, CBK, tüzük, yönetmelik ve tebliğlerin güncel
metinlerini mevzuat.gov.tr'den alır ve icerik/<tür>/ altına yazar.

Eşleştirme: kanunlarda numara, diğerlerinde başlık + Resmî Gazete tarihi.
Kayıt kimliği korunur, böylece sitedeki adresler değişmez.
Sonuçlar kaynak-isleme/mevzuat-gov/eslesme.json dosyasında tutulur (yeniden
çalıştırıldığında yalnızca eksikler aranır).

Kullanım: python araclar/mevzuat_gov_aktar.py [--sinir 20]
"""
import argparse, html, http.cookiejar, json, re, sys, time, unicodedata, urllib.parse, urllib.request
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "araclar"))
from site_uret import belgeleri_oku, sade  # noqa: E402

TABAN = "https://www.mevzuat.gov.tr"
ESLESME = KOK / "kaynak-isleme" / "mevzuat-gov" / "eslesme.json"
ARAMA_TUR = {"kanun": ["Kanun", "MulgaKanun"], "khk": ["KHK"], "cbk": ["CumhurbaskaniKararnameleri"],
             "tuzuk": ["Tuzuk"], "teblig": ["Teblig"],
             "yonetmelik": ["TumYonetmelik"]}
UA = "Mozilla/5.0 (CanliSaglikMevzuati)"


class Istemci:
    def __init__(self):
        self.baslat()

    def baslat(self):
        self.kavanoz = http.cookiejar.CookieJar()
        self.acici = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.kavanoz))
        self.acici.addheaders = [("User-Agent", UA)]
        ana = self.al(TABAN + "/").decode("utf-8", "replace")
        m = re.search(r'antiforgerytoken" type="hidden" value="([^"]+)"', ana)
        self.token = m.group(1) if m else ""

    def al(self, url, veri=None, basliklar=None, deneme=3):
        for i in range(deneme):
            try:
                istek = urllib.request.Request(url, data=veri, headers=basliklar or {})
                with self.acici.open(istek, timeout=60) as r:
                    return r.read()
            except Exception:
                if i == deneme - 1:
                    raise
                time.sleep(3 * (i + 1))

    def ara(self, tur, ifade="", no=""):
        govde = {"draw": 1, "start": 0, "length": 25, "parameters": {
            "MevzuatTur": tur, "YonetmelikMevzuatTur": "OsmanliKanunu", "AranacakIfade": ifade,
            "TamCumle": "true" if ifade else "false", "AranacakYer": "2", "MevzuatNo": no,
            "BaslangicTarihi": "", "BitisTarihi": "", "antiforgerytoken": self.token}}
        for deneme in range(4):
            govde["parameters"]["antiforgerytoken"] = self.token
            ham = self.al(TABAN + "/Anasayfa/MevzuatDatatable", json.dumps(govde).encode(),
                          {"Content-Type": "application/json; charset=utf-8", "X-Requested-With": "XMLHttpRequest"})
            time.sleep(1.2)
            try:
                sonuc = json.loads(ham).get("data") or []
                break
            except json.JSONDecodeError:
                # Oturum düştü ya da hız sınırına takıldı: bekle, yeni oturum aç
                time.sleep(15 * (deneme + 1))
                self.baslat()
        else:
            raise RuntimeError("arama yanıtı alınamadı")
        for s in sonuc:
            s["mevAdi"] = html.unescape(re.sub(r"<[^>]+>", "", s.get("mevAdi") or ""))
        return sonuc

    def metin(self, tur_no, no, tertip):
        url = f"{TABAN}/anasayfa/MevzuatFihristDetayIframe?MevzuatTur={tur_no}&MevzuatNo={no}&MevzuatTertip={tertip}"
        time.sleep(0.7)
        return self.al(url).decode("utf-8", "replace")


def tarih_iso(t):
    m = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", t or "")
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else ""


def anahtar(s):
    s = re.sub(r"\(.*?\)", " ", s or "")
    return sade(s)


def eslestir(ist, b):
    url = b.get("kaynak_url") or ""
    m = re.search(r"MevzuatNo=(\d+)&MevzuatTur=(\d+)&MevzuatTertip=(\d+)", url)
    m2 = re.search(r"MevzuatKod=(\d+)\.(\d+)\.(\d+)", url)
    if m or m2:
        no, tur, tertip = (m.group(1), m.group(2), m.group(3)) if m else (m2.group(3), m2.group(1), m2.group(2))
        return {"mevzuatNo": no, "mevzuatTur": int(tur), "mevzuatTertip": tertip, "mevAdi": b["baslik"],
                "resmiGazeteTarihi": "", "resmiGazeteSayisi": ""}
    turler = ARAMA_TUR.get(b["tur"], [])
    adaylar = []
    for t in turler:
        if b["tur"] == "kanun" and b.get("sayi", "").isdigit():
            adaylar += ist.ara(t, no=b["sayi"])
        if not adaylar:
            ifade = re.sub(r"\s*\(.*?\)\s*", " ", b["baslik"]).strip()
            adaylar += ist.ara(t, ifade=ifade)
        if not adaylar and b["tur"] != "kanun":
            # Başlıktaki tür sözcüğü olmadan, gevşek arama
            kisa = re.sub(r"\s*\(.*?\)\s*", " ", b["baslik"])
            kisa = re.sub(r"\s+(Hakkında|Dair|İlişkin)?\s*(Yönetmeli[kğ]\w*|Tüzü[kğ]\w*|Tebliğ\w*|Nizamname\w*)\s*$", "", kisa).strip()
            if len(kisa) > 12:
                adaylar += ist.ara(t, ifade=kisa)
        if adaylar:
            break
    hedef = anahtar(b["baslik"])
    en_iyi, puan = None, 0
    for a in adaylar:
        ad = anahtar(a.get("mevAdi", ""))
        p = 0
        if ad == hedef:
            p += 10
        elif hedef and (hedef in ad or ad in hedef):
            p += 5
        if b["tur"] == "kanun" and str(a.get("mevzuatNo")) == b.get("sayi"):
            p += 10
        if b.get("rg_tarih") and tarih_iso(a.get("resmiGazeteTarihi")) == b["rg_tarih"]:
            p += 6
        if p > puan:
            en_iyi, puan = a, p
    return en_iyi if puan >= 10 else None


MADDE = re.compile(r"^((?:GEÇİCİ |Geçici |EK |Ek |MÜKERRER )?(?:MADDE|Madde)\s*\d+[/A-Za-z]*)\s*[-–—:]\s*")


def temiz(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip()


def html_md(sayfa):
    sayfa = re.sub(r"(?is)<(script|style|head)[^>]*>.*?</\1>", " ", sayfa)
    sayfa = re.sub(r"(?is)<a[^>]*href=\"#_ftn\d+\"[^>]*>.*?</a>", lambda m: "[" + re.sub(r"\D", "", temiz(m.group(0))) + "]", sayfa)
    bloklar = []
    for m in re.finditer(r"(?is)<table.*?</table>|<p[ >].*?</p>|<h\d[^>]*>.*?</h\d>", sayfa):
        parca = m.group(0)
        if parca.lower().startswith("<table"):
            satirlar = []
            for tr in re.findall(r"(?is)<tr.*?</tr>", parca):
                hucreler = [temiz(td).replace("|", "/") for td in re.findall(r"(?is)<t[dh].*?</t[dh]>", tr)]
                if any(hucreler):
                    satirlar.append("| " + " | ".join(hucreler) + " |")
            # Tek hücreli düzen tabloları metin olarak kalsın
            if satirlar and all(s.count("|") <= 2 for s in satirlar):
                bloklar += [s.strip("| ").strip() for s in satirlar]
            elif satirlar:
                bloklar.append("\n".join(satirlar))
            continue
        t = temiz(parca)
        if t and t != "\xa0":
            bloklar.append(t)
    cikti = []
    for i, t in enumerate(bloklar):
        if "\n" in t:
            cikti.append(t)
            continue
        sonraki = bloklar[i + 1] if i + 1 < len(bloklar) else ""
        m = MADDE.match(t)
        harfler = [c for c in t if c.isalpha()]
        if m:
            cikti.append(f"**{re.sub(chr(32) + '+', ' ', m.group(1))} –** {t[m.end():]}")
        elif harfler and len(t) < 160 and sum(c.isupper() for c in harfler) / len(harfler) > 0.85:
            cikti.append("### " + t)
        elif MADDE.match(sonraki) and len(t) < 110 and not re.search(r"[.:;,]$", t):
            cikti.append("#### " + t)
        elif re.match(r"^\[\d+\]\s", t):
            cikti.append("<small>" + t + "</small>")
        else:
            cikti.append(t)
    return "\n\n".join(cikti) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sinir", type=int, default=0)
    a = ap.parse_args()
    eslesme = json.loads(ESLESME.read_text(encoding="utf-8")) if ESLESME.exists() else {}
    ist = Istemci()
    belgeler = belgeleri_oku()
    hedefler = [b for b in belgeler.values() if not b["tam_metin"] and b["tur"] in ARAMA_TUR]
    print(len(hedefler), "künye kaydı aranacak", flush=True)
    yazilan = 0
    for i, b in enumerate(hedefler):
        if a.sinir and i >= a.sinir:
            break
        kayit = eslesme.get(b["id"])
        if kayit is None:
            try:
                bul = eslestir(ist, b)
            except Exception as hata:
                print("  ! arama hatası:", b["baslik"][:60], hata, flush=True)
                continue
            kayit = {"no": bul["mevzuatNo"], "tur": bul["mevzuatTur"], "tertip": bul["mevzuatTertip"],
                     "ad": bul["mevAdi"], "rg_tarih": tarih_iso(bul.get("resmiGazeteTarihi")),
                     "rg_sayi": bul.get("resmiGazeteSayisi") or ""} if bul else {}
            eslesme[b["id"]] = kayit
            ESLESME.parent.mkdir(parents=True, exist_ok=True)
            ESLESME.write_text(json.dumps(eslesme, ensure_ascii=False, indent=1), encoding="utf-8")
        if not kayit:
            continue
        try:
            govde = html_md(ist.metin(kayit["tur"], kayit["no"], kayit["tertip"]))
        except Exception as hata:
            print("  ! metin alınamadı:", b["baslik"][:60], hata, flush=True)
            continue
        if len(govde) < 300:
            continue
        url = f"{TABAN}/mevzuat?MevzuatNo={kayit['no']}&MevzuatTur={kayit['tur']}&MevzuatTertip={kayit['tertip']}"
        veri = {"id": b["id"], "baslik": b["baslik"], "tur": b["tur"], "tarih": b.get("tarih", ""),
                "sayi": b.get("sayi", ""), "rg_tarih": b.get("rg_tarih") or kayit["rg_tarih"],
                "rg_sayi": b.get("rg_sayi") or kayit["rg_sayi"], "birim": b.get("birim", ""), "konu": b.get("konu", ""),
                "etiketler": b.get("etiketler", []), "kaynak": "Mevzuat Bilgi Sistemi (mevzuat.gov.tr), güncel metin",
                "kaynak_url": url, "not": b.get("not", ""), "durum": b.get("durum", "yürürlükte")}
        on = ["---"] + [f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in veri.items() if v not in ("", [], None)] + ["---"]
        hedef = KOK / "icerik" / b["tur"] / f"{b['id']}.md"
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_text("\n".join(on) + "\n\n" + govde, encoding="utf-8")
        yazilan += 1
        if yazilan % 10 == 0:
            print(f"  {yazilan} tam metin yazıldı ({i + 1}/{len(hedefler)})", flush=True)
    bulunamayan = [b["baslik"] for b in hedefler if not eslesme.get(b["id"])]
    print(f"{yazilan} tam metin yazıldı; {len(bulunamayan)} kayıt mevzuat.gov.tr'de bulunamadı")


if __name__ == "__main__":
    main()

