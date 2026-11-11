#!/usr/bin/env python3
"""icerik/ ve kaynak-isleme/katalog/ altındaki verilerden statik siteyi üretir.

Çıktı: _site/ (GitHub Pages ile yayımlanır)
Her tam metinli belge için HTML sayfa, .docx ve .pdf dosyası oluşturulur.

Kullanım: python araclar/site_uret.py [--hizli]   (--hizli: Word/PDF üretme)
"""
import argparse, datetime as dt, html, json, re, shutil, sys, unicodedata
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
CIKTI = KOK / "_site"
import hashlib as _hl
STIL_SURUM = _hl.md5((KOK / "site" / "assets" / "stil.css").read_bytes()).hexdigest()[:8]
ARA_SURUM = _hl.md5((KOK / "site" / "assets" / "ara.js").read_bytes()).hexdigest()[:8]
import time as _time
SITE_SURUM = str(int(_time.time()))
SITE_ADI = "Canlı Sağlık Mevzuatı"

TUR_ADLARI = {
    "kanun": "Kanunlar ve Kanun Hükmünde Kararnameler",
    "cbk": "Cumhurbaşkanlığı Kararnameleri",
    "khk": "Kanun Hükmünde Kararnameler",
    "bkk": "Bakanlar Kurulu Kararları",
    "tuzuk": "Tüzükler",
    "yonetmelik": "Yönetmelikler",
    "yonerge": "Yönergeler",
    "genelge": "Genelgeler",
    "teblig": "Tebliğler",
    "protokol": "Protokoller",
    "yazi": "Resmî Yazılar ve Talimatlar",
}
# Listede/menüde birlikte gösterilen türler: KHK'ler Kanunlar bölümünde listelenir
GRUP = {"khk": "kanun"}


def grup(t):
    return GRUP.get(t, t)


TUR_TEKIL = {
    "kanun": "Kanun", "cbk": "Cumhurbaşkanlığı Kararnamesi", "khk": "Kanun Hükmünde Kararname", "bkk": "Bakanlar Kurulu Kararı",
    "tuzuk": "Tüzük", "yonetmelik": "Yönetmelik", "yonerge": "Yönerge", "genelge": "Genelge",
    "teblig": "Tebliğ", "protokol": "Protokol", "yazi": "Resmî Yazı",
}


# ---------------------------------------------------------------- veri okuma
def on_bilgi_ayir(metin):
    metin = unicodedata.normalize("NFC", metin)
    if not metin.startswith("---\n"):
        return {}, metin
    son = metin.find("\n---\n", 4)
    if son < 0:  # bozuk künye (kapanış çizgisi yok): yayını durdurma, künyesiz işle
        print("UYARI: künye kapanışı yok", metin[4:120].splitlines()[:1], file=sys.stderr)
        return {}, metin[4:]
    veri = {}
    for satir in metin[4:son].splitlines():
        if ":" in satir:
            k, v = satir.split(":", 1)
            v = v.strip()
            try:
                veri[k.strip()] = json.loads(v)
            except json.JSONDecodeError:  # elle/ajanla yazılmış tırnaksız değerler
                if v in ("true", "false"):
                    veri[k.strip()] = v == "true"
                else:
                    veri[k.strip()] = v.strip('"').strip("'")
    return veri, metin[son + 5:]


def belgeleri_oku():
    global _ES_DIZIN
    tam = []
    ek = {}
    elle = {}  # elle-duzeltme.json: her alanı zorla değiştirir
    for js in sorted((KOK / "kaynak-isleme" / "zenginlestirme").glob("*.json")):
        hedef = elle if js.stem == "elle-duzeltme" else ek
        for i, v in json.loads(js.read_text(encoding="utf-8")).items():
            hedef.setdefault(i, {}).update(v)
    for md in sorted((KOK / "icerik").glob("*/*.md")):
        veri, govde = on_bilgi_ayir(md.read_text(encoding="utf-8"))
        # Bozuk künyelere dayanıklılık: kimlik ve tür dosya yolundan tamamlanır
        veri.setdefault("id", md.stem)
        veri.setdefault("tur", md.parent.name)
        veri.setdefault("baslik", md.stem.replace("-", " "))
        for alan, deger in ek.get(veri["id"], {}).items():
            if deger and (not veri.get(alan) or alan in ("baslik", "konu", "etiketler")):
                veri[alan] = deger
        veri.update({a: d for a, d in elle.get(veri["id"], {}).items() if a != "gizle"})
        alanlari_duzelt(veri)
        veri["govde"] = govde
        veri["tam_metin"] = True
        tam.append(veri)
    belgeler = tekillestir(tam)
    # Tam metni olan (ya da tam metne birleştirilmiş) kimlikler katalogda yeniden künye olarak görünmesin
    bilinen = set(belgeler)
    sahip = {i: b for b in belgeler.values() for _, i in b.get("eski_kimlikler", [])}
    sahip.update(belgeler)
    for b in belgeler.values():
        bilinen.update(i for _, i in b.get("eski_kimlikler", []))
    # Site sahibinin isteğiyle yedek/ klasörüne taşınan belgeler katalogdan künye olarak geri gelmesin
    yedek_id, yedek_anahtar, yedek_no = set(), set(), set()
    for md in sorted((KOK / "yedek").rglob("*.md")):
        y, _ = on_bilgi_ayir(md.read_text(encoding="utf-8"))
        if not y.get("baslik"):
            continue
        y.setdefault("id", md.stem)
        yedek_id.add(y["id"])
        yedek_anahtar.add(baslik_anahtari(y))
        if y.get("tur") in ("kanun", "khk") and y.get("sayi"):
            yedek_no.add((y["tur"], str(y["sayi"])))
    for js in sorted((KOK / "kaynak-isleme" / "katalog").glob("*.json")):
        for k in json.loads(js.read_text(encoding="utf-8")):
            if k.get("tur") not in TUR_ADLARI or not k.get("baslik"):
                continue
            k["baslik"] = unicodedata.normalize("NFC", " ".join(k["baslik"].split()))
            k["etiketler"] = [t.replace("-", " ") for t in k.get("etiketler", []) if t]
            if not k.get("id"):
                k["id"] = "k-" + sade(k["baslik"]).replace(" ", "-")[:90]
            if k["id"] in bilinen or elle.get(k["id"], {}).get("gizle"):
                continue
            esi = sahip.get(elle.get(k["id"], {}).get("esi", ""))
            if esi:  # elle belirlenmiş: bu künye, tam metni olan başka bir kaydın kopyası
                esi.setdefault("eski_kimlikler", []).append((k["tur"], k["id"]))
                for alan in ("tarih", "sayi", "rg_tarih", "rg_sayi", "birim", "konu"):
                    if k.get(alan) and not esi.get(alan):
                        esi[alan] = k[alan]
                continue
            for alan, deger in ek.get(k["id"], {}).items():
                if deger and (not k.get(alan) or alan in ("baslik", "konu", "etiketler")):
                    k[alan] = deger
            k.update({a: d for a, d in elle.get(k["id"], {}).items() if a != "gizle"})
            alanlari_duzelt(k)
            # Tam metni olan belgeyle aynıysa yalnızca eksik alanları tamamla
            es = esini_bul(belgeler, k)
            if es:
                for alan in ("kaynak_url", "rg_tarih", "rg_sayi", "degisiklikler", "tarih", "sayi", "birim", "konu"):
                    if k.get(alan) and not es.get(alan):
                        es[alan] = k[alan]
                if k.get("kaynak") and k["kaynak"] != es.get("kaynak") and k["kaynak"] not in es.get("diger_kaynaklar", []):
                    es.setdefault("diger_kaynaklar", []).append(k["kaynak"])
                if k.get("durum") and k["durum"] != "yürürlükte":
                    es["durum"] = k["durum"]
                continue
            if (k["id"] in yedek_id or baslik_anahtari(k) in yedek_anahtar
                    or (k.get("tur") in ("kanun", "khk") and (k["tur"], str(k.get("sayi", ""))) in yedek_no)):
                continue
            k["tam_metin"] = False
            k.setdefault("durum", "yürürlükte")
            belgeler.setdefault(k["id"], k)
            _ES_DIZIN = None
    sonuc = ciftleri_birlestir(belgeler)
    for b in sonuc.values():
        b["baslik"] = ad_temizle(b)
        degisiklik_listesi_ekle(b)
        son_degisiklik_bul(b)
    return sonuc


SD_TURLERI = {"kanun", "khk", "cbk", "bkk", "tuzuk", "yonetmelik"}


def son_degisiklik_bul(b):
    """Kanun/KHK/CBK/BKK/tüzük/yönetmelik için son değişikliğin tarihi: sayfa sonundaki değişiklik listesindeki
    ve metindeki (Değişik/Ek/Mülga: … RG-g/a/yyyy) notlarındaki en yeni tarih; değişiklik yoksa mevzuatın tarihi."""
    if b.get("tur") not in SD_TURLERI:
        return
    taban = b.get("tarih") or b.get("rg_tarih") or ""
    bugun = dt.date.today().isoformat()
    tarihler = []
    govde = b.get("govde") or ""
    i = govde.find("## DEĞİŞİKLİK LİSTESİ")
    if i >= 0:
        for g, a, y in re.findall(r"(?<![\d/.])(\d{1,2})[./](\d{1,2})[./](\d{4})(?![\d/.])", govde[i:]):
            tarihler.append(f"{y}-{int(a):02d}-{int(g):02d}")
    for n in _NOT.finditer(govde):
        if re.search(r"Değişik|Ek|Mülga|İptal|Yürürlükten|Kaldırıl", n[1]):
            tarihler.append(f"{n[5]}-{int(n[4]):02d}-{int(n[3]):02d}")
    tarihler = [x for x in tarihler if "1900" <= x <= bugun and x > (b.get("rg_tarih") or taban or "0")]
    b["son_degisiklik"] = max(tarihler) if tarihler else taban


# ---------------------------------------------------------------- değişiklik listesi
# Kanun/KHK/CBK/tüzük/yönetmelik sayfalarının sonuna değişiklik listesi tablosu eklenir:
# mevzuat.gov.tr'deki resmî liste varsa o (kaynak-isleme/mevzuat-gov/degisiklik-listeleri.json),
# yoksa metindeki "(Değişik: …)", "(Ek: RG-…)" notlarından derlenen liste.
_DL = None
_LISTE_TURLER = ("kanun", "khk", "cbk", "tuzuk", "yonetmelik")
_NOT = re.compile(r"\(([^()]{0,70}?)\s*:\s*(RG\s*[-–]\s*)?(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})\s*[-–]\s*([^()]{1,80}?)\)")
_GOVDE_LISTE = re.compile(r"(?im)^[^\n]*(?:GÖSTERİR\s+(?:LİSTE|TABLO|CETVEL)|YÜRÜRLÜĞE\s+GİRİŞ\s+TARİH(?:LERİNİ|İNİ))[^\n]*$")


def _hucre(s):
    return " ".join(str(s).replace("|", "/").split())


def _md_tablo(satirlar):
    n = max(len(r) for r in satirlar)
    return "\n".join("| " + " | ".join(_hucre(h) for h in (r + [""] * (n - len(r)))) + " |" for r in satirlar)


def _govdeden_liste(b):
    """Metindeki değişiklik notlarından (değiştiren, tarih) -> maddeler listesi."""
    yon = b["tur"] in ("yonetmelik", "tuzuk")
    gruplar, madde = {}, ""
    for satir in b["govde"].split("\n"):
        m = re.match(r"^\W*(GEÇİCİ MADDE|Geçici Madde|EK MADDE|Ek Madde|MADDE|Madde)\s*[-–]?\s*(\d+[/A-Za-z]*)", satir)
        if m:
            on = m[1].lower()
            madde = ("Geçici Madde " if on.startswith("geçici") else "Ek Madde " if on.startswith("ek") else "") + m[2]
        for n in _NOT.finditer(satir):
            if not re.search(r"Değişik|Ek|Mülga|İptal|Yürürlükten|Kaldırıl", n[1]):
                continue
            g, d, a, y = n[6], int(n[3]), int(n[4]), n[5]
            if re.search(r"C[KB]K?\s*[-/]\s*(\d+)", g):
                kim = "CBK/" + re.search(r"C[KB]K?\s*[-/]\s*(\d+)", g)[1]
            elif re.search(r"KHK\s*[-/]\s*(\d+)", g):
                kim = "KHK/" + re.search(r"KHK\s*[-/]\s*(\d+)", g)[1]
            else:
                ilk = re.match(r"\s*(\d+)", g)
                if not ilk:
                    continue
                kim = ("RG " if (n[2] or yon) else "") + ilk[1]
            anahtar = (y, a, d, kim)
            gruplar.setdefault(anahtar, [])
            if madde and madde not in gruplar[anahtar]:
                gruplar[anahtar].append(madde)
    if not gruplar:
        return None
    if yon:
        bas = ["Resmî Gazete tarihi", "Resmî Gazete sayısı", "Değişen maddeler"]
        satirlar = [[f"{d}/{a}/{y}", kim.replace("RG ", ""), ", ".join(sorted(m, key=_madde_sirasi)) or "–"] for (y, a, d, kim), m in sorted(gruplar.items())]
        rt = re.match(r"(\d{4})-(\d{2})-(\d{2})", b.get("rg_tarih", "") or "")
        if rt:
            satirlar.insert(0, [f"{int(rt[3])}/{int(rt[2])}/{rt[1]}", b.get("rg_sayi", "") or "–", "İlk yayım"])
    else:
        bas = ["Değiştiren mevzuat", "Değişen veya eklenen maddeler", "Tarih"]
        satirlar = [[kim, ", ".join(sorted(m, key=_madde_sirasi)) or "–", f"{d}/{a}/{y}"] for (y, a, d, kim), m in sorted(gruplar.items())]
    return [bas] + satirlar


def _govde_listesini_sil(govde):
    """Metnin içindeki eski değişiklik listesini (başlık + tablo/satırlar) çıkarır; öncesi ve sonrası korunur."""
    bloklar = re.split(r"\n{2,}", govde)
    for i, bl in enumerate(bloklar):
        duz = re.sub(r"[#*|]", " ", bl)
        yon = re.search(r"(?:Yönetmeliğin|Tüzüğün|YÖNETMELİĞİN|TÜZÜĞÜN)\s+Yayımlandığı\s+Resm[iî]\s+Gazete|YAYIMLANDIĞI\s+RESM[İÎ]\s+GAZETE", duz)
        if len(duz) < 400 and (yon or re.search(r"GÖSTERİR\s+(?:LİSTE|TABLO|CETVEL)|YÜRÜRLÜĞE\s+GİRİŞ\s+TARİH", duz) and duz.upper() == duz):
            bas = i
            while bas > 0 and i - bas < 4 and bloklar[bas - 1].lstrip().startswith("#") and bloklar[bas - 1].upper() == bloklar[bas - 1] \
                    and re.search(r"SAYILI|MEVZUAT|DEĞİŞİKLİK|HÜKÜM|İPTAL|EDİLEN|YÜRÜRLÜĞE|ANAYASA|KARAR", bloklar[bas - 1]):
                bas -= 1
            son = i + 1
            while son < len(bloklar):
                b2 = bloklar[son].strip()
                if b2.startswith("|") or (b2.startswith("#") and b2.upper() == b2) or \
                        (len(b2) < 300 and not re.match(r"^(\**(MADDE|Madde|EK MADDE|GEÇİCİ)|<small>)", b2)):
                    son += 1
                else:
                    break
            return "\n\n".join(bloklar[:bas] + bloklar[son:])
    return None


def _tablo_korunur(govde, yeni):
    """Silinecek kısımda en az üç satırlık markdown tablo varsa metindeki liste düzgündür."""
    silinen = set(govde.split("\n")) - set(yeni.split("\n"))
    return sum(1 for x in silinen if x.strip().startswith("|")) >= 3


def _madde_sirasi(m):
    n = re.match(r"(?:(Ek|Geçici) Madde )?(\d+)", m)
    return ({None: 0, "Ek": 1, "Geçici": 2}[n[1]] if n else 3, int(n[2]) if n else 0, m)


def _yonetmelik_tablosu(b, govde, yeni):
    """Metindeki düzensiz 'Yönetmeliğin Yayımlandığı Resmî Gazete' tablosunu temiz satırlara çevirir."""
    kalan = set(yeni.split("\n"))
    rg = []
    for ln in govde.split("\n"):
        if ln in kalan or not ln.strip().startswith("|"):
            continue
        h = [c.strip() for c in ln.strip().strip("|").split("|")]
        for j, c in enumerate(h):
            if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", c):
                rg.append((c, h[j + 1] if j + 1 < len(h) else ""))
                break
    if not rg:
        return None
    maddeler = {}
    tur = _govdeden_liste(dict(b, govde=govde)) or []
    for r in tur[1:]:
        if r[2] != "İlk yayım":
            maddeler[re.sub(r"\D.*", "", r[1])] = r[2]
    satirlar = [[rg[0][0], rg[0][1], "İlk yayım"]]
    gorulen = set()
    for t, n in rg[1:]:
        anahtar = re.sub(r"\D.*", "", n)
        gorulen.add(anahtar)
        satirlar.append([t, n, maddeler.get(anahtar, "–")])
    for r in tur[1:]:  # tabloda olmayan ama metinde notu bulunan değişiklikler
        anahtar = re.sub(r"\D.*", "", r[1])
        if r[2] != "İlk yayım" and anahtar not in gorulen and anahtar != re.sub(r"\D.*", "", rg[0][1]):
            satirlar.append(r)
    def tarih(r):
        g, a, y = (int(x) for x in r[0].split("/"))
        return (y, a, g)
    satirlar = [satirlar[0]] + sorted(satirlar[1:], key=tarih)
    return [["Resmî Gazete tarihi", "Resmî Gazete sayısı", "Değişen maddeler"]] + satirlar


def degisiklik_listesi_ekle(b):
    global _DL
    if b.get("tur") not in _LISTE_TURLER or not b.get("tam_metin"):
        return
    if _DL is None:
        yol = KOK / "kaynak-isleme" / "mevzuat-gov" / "degisiklik-listeleri.json"
        _DL = json.loads(yol.read_text(encoding="utf-8")) if yol.exists() else {}
    resmi = None
    for i in [b["id"]] + [i for _, i in b.get("eski_kimlikler", [])]:
        if _DL.get(i, {}).get("satirlar"):
            resmi = _DL[i]
            break
    govde = b["govde"]
    yeni = _govde_listesini_sil(govde)
    if resmi:
        if yeni is not None:  # metindeki (çoğu zaman bozuk) listeyi kaldır, yerine resmî tabloyu koy
            govde = yeni
        ek = (f"\n\n## DEĞİŞİKLİK LİSTESİ\n\n<small>Kaynak: mevzuat.gov.tr</small>\n\n### {_hucre(resmi.get('baslik') or '')}\n\n"
              + _md_tablo(resmi["satirlar"]))
    else:
        if yeni is not None:
            if b["tur"] in ("yonetmelik", "tuzuk"):
                liste = _yonetmelik_tablosu(b, govde, yeni)
                if liste:
                    b["govde"] = yeni.rstrip() + ("\n\n## DEĞİŞİKLİK LİSTESİ\n\n<small>Resmî Gazete bilgileri mevzuat.gov.tr metninden, "
                                                  "değişen maddeler metindeki değişiklik notlarından derlenmiştir.</small>\n\n") + _md_tablo(liste) + "\n"
                    return
            if _tablo_korunur(govde, yeni):
                return  # metinde düzgün tablo halinde liste var
            govde = yeni
        liste = _govdeden_liste(b)
        if not liste:
            return
        ek = ("\n\n## DEĞİŞİKLİK LİSTESİ\n\n<small>Bu liste metindeki değişiklik notlarından derlenmiştir.</small>\n\n"
              + _md_tablo(liste))
    b["govde"] = govde.rstrip() + ek + "\n"


def ad_temizle(b):
    """Görünen addan sondaki tarih/sayı eklerini siler; tarih ve sayı künye tablosunda ayrıca gösterilir.
    (Kayıt eşleştirmesi ham adla yapıldığı için bu yalnız gösterimde uygulanır.)"""
    ilk = t = b.get("baslik", "")
    if b.get("tur") == "genelge":
        return t
    onceki = None
    while onceki != t:  # "(Karar Sayısı: 477) (19.12.2018)" gibi üst üste ekler
        onceki = t
        m = re.search(r"\s*\((?:Karar Sayısı|Kararname Numarası|No)\s*:\s*([\d/]+)\)\s*$", t)
        if m:
            b.setdefault("sayi", "") or b.update(sayi=m[1])
            t = t[:m.start()]
        t = re.sub(r"\s*\((?:\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4}[^)]*|\d{4}|[^)]*Makam Onayı[^)]*|\d{1,2} \w+ \d{4} tarih[^)]*Resm[iî] Gazete)\)\s*$", "", t)
        if b.get("tur") in ("teblig", "yonerge"):
            m = re.search(r"\s*\(?(\d{4}\s*/\s*\d+)(?:\s*-\s*\d+)?\)?\s*$", t)
            if m:
                if not b.get("sayi"):
                    b["sayi"] = re.sub(r"\s", "", m[1])
                t = t[:m.start()]
    return t.strip() or ilk


def tarih_iso(t):
    t = str(t or "").strip()
    m = re.fullmatch(r"(\d{1,2})\s*[./-]\s*(\d{1,2})\s*[./-]\s*(\d{4})", t)
    if m and 1 <= int(m[2]) <= 12 and 1 <= int(m[1]) <= 31:
        return f"{m[3]}-{int(m[2]):02d}-{int(m[1]):02d}"
    return t


def no_sade(s):
    """2023/03 ile 2023/3 aynı numaradır."""
    return re.sub(r"(?<=/)0+(?=\d)", "", re.sub(r"\s+", "", str(s or "")))


def alanlari_duzelt(b):
    # "Tarihi:07.06.1935 Sayısı:2767 R.G. Tarihi:… R.G. Sayısı:… Kanun Adı" -> yalnız ad (künye tabloda gösteriliyor)
    if b.get("baslik"):
        b["baslik"] = re.sub(r"^(?:\s*(?:Tarihi?|Sayısı|R\.\s*G\.\s*(?:Tarihi|Sayısı))\s*:\s*[\d./]+)+\s*", "", b["baslik"]) or b["baslik"]
    for alan in ("tarih", "rg_tarih"):
        if b.get(alan):
            b[alan] = tarih_iso(b[alan])
    if b.get("tarih", "").startswith("1905-"):  # hatalı dönüştürülmüş tablo değeri
        b["tarih"] = ""
    # Genelge numarası başlıkta yazılıysa sayı alanına taşı
    if b.get("tur") == "genelge" and not b.get("sayi"):
        m = re.search(r"\((\d{4})\s*/\s*(\d{1,3})\)", b.get("baslik", ""))
        if m:
            b["sayi"] = f"{m[1]}/{m[2]}"


def baslik_ozu(b):
    s = sade(re.sub(r"\(.*?\)", " ", b.get("baslik", "")))
    s = re.sub(r"\b(yonergesi|yonerge|yonetmeligi|yonetmelik|genelgesi|genelge|tebligi|teblig|hakkinda|dair|iliskin"
               r"|ile ilgili|uygulama|esaslari|usul ve esaslar)\b", " ", s)
    return " ".join(s.split())


def belge_yili(b):
    for kaynak in (b.get("tarih", ""), no_sade(b.get("sayi", ""))):
        m = re.match(r"((?:19|20)\d{2})(?:-|/|$)", kaynak)
        if m:
            return m[1]
    m = re.search(r"\(((?:19|20)\d{2})(?:\s*/\s*\d+)?\)", b.get("baslik", ""))
    return m[1] if m else ""


def celisir(a, b):
    """İki kayıt farklı belgeleri mi gösteriyor (tarih, sayı ya da yıl farklı)?"""
    iso = lambda t: re.fullmatch(r"\d{4}-\d{2}-\d{2}", t or "")
    if iso(a.get("tarih")) and iso(b.get("tarih")):
        return a["tarih"] != b["tarih"]
    sa, sb = no_sade(a.get("sayi")), no_sade(b.get("sayi"))
    if sa and sb and sa != sb:
        return True
    ya, yb = belge_yili(a), belge_yili(b)
    return bool(ya and yb and ya != yb)


def metin_benzer(a, b):
    import difflib
    x, y = sade(a.get("govde", ""))[:4000], sade(b.get("govde", ""))[:4000]
    if not x or not y:
        return False
    return difflib.SequenceMatcher(None, x, y).ratio() >= 0.8


def birlestir(ana, diger):
    # Daha eksiksiz başlığı koru (ör. kısaltma ve "Yönergesi" eki olan)
    if len(diger.get("baslik", "")) > len(ana.get("baslik", "")) and sade(ana.get("baslik", "")) in sade(diger["baslik"]) \
            and "degisik" not in sade(diger["baslik"]):
        ana["baslik"] = diger["baslik"]
    ana.setdefault("eski_kimlikler", []).append((diger["tur"], diger["id"]))
    ana["eski_kimlikler"] += diger.get("eski_kimlikler", [])
    for alan in ("tarih", "sayi", "rg_tarih", "rg_sayi", "birim", "konu", "etiketler", "kaynak_url"):
        if diger.get(alan) and not ana.get(alan):
            ana[alan] = diger[alan]
    if diger.get("kaynak") and diger["kaynak"] != ana.get("kaynak") and diger["kaynak"] not in ana.get("diger_kaynaklar", []):
        ana.setdefault("diger_kaynaklar", []).append(diger["kaynak"])


def ciftleri_birlestir(belgeler):
    """Aynı belgenin farklı adlarla girilmiş kopyalarını tek kayıtta toplar.
    Aynı tür + aynı tarih + aynı sayı ya da aynı başlık özü (tarih/sayı çelişmiyorsa;
    iki tam metin varsa metinler de benzer olmalı) aynı belge sayılır."""
    tercih = lambda b: (b["tam_metin"], oncelik(b) if b["tam_metin"] else 0, len(b.get("baslik", "")))
    gruplar = {}
    for b in belgeler.values():
        if b["tur"] == "yazi":
            continue
        anahtarlar = [("oz", b["tur"], baslik_ozu(b))]
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", b.get("tarih", "")) and len(no_sade(b.get("sayi"))) >= 3:
            anahtarlar.append(("ts", b["tur"], b["tarih"], no_sade(b["sayi"]).split("-")[0]))
        for k in anahtarlar:
            gruplar.setdefault(k, []).append(b)
    silinen = set()
    for k, grup in gruplar.items():
        grup = [b for b in grup if b["id"] not in silinen]
        if len(grup) < 2:
            continue
        grup.sort(key=tercih, reverse=True)
        kumeler = []
        for b in grup:
            for kume in kumeler:
                bas = kume[0]
                if k[0] == "ts":
                    import difflib
                    if b["tam_metin"] and bas["tam_metin"]:
                        k1 = {w[:6] for w in baslik_ozu(b).split() if len(w) > 2}
                        k2 = {w[:6] for w in baslik_ozu(bas).split() if len(w) > 2}
                        ortusme = len(k1 & k2) / max(1, min(len(k1), len(k2)))
                        uygun = metin_benzer(b, bas) or ortusme >= 0.8
                    else:
                        uygun = difflib.SequenceMatcher(None, baslik_ozu(b), baslik_ozu(bas)).ratio() >= 0.6
                else:
                    uygun = (not any(celisir(b, u) for u in kume)
                             and (not (b["tam_metin"] and bas["tam_metin"]) or metin_benzer(b, bas)))
                if uygun:
                    kume.append(b)
                    break
            else:
                kumeler.append([b])
        for kume in kumeler:
            for diger in kume[1:]:
                birlestir(kume[0], diger)
                silinen.add(diger["id"])
    return {i: b for i, b in belgeler.items() if i not in silinen}


def baslik_anahtari(b):
    s = re.sub(r"^\s*(\d+\.)+\d*\s*", "", b.get("baslik", ""))
    if b.get("tur") == "genelge" and re.fullmatch(r"\d{4}/\d+", b.get("sayi", "")):
        return ("genelge", "no:" + b["sayi"])
    s = re.sub(r"\(\s*\d{4}\s*/\s*\d+\s*\)", "", s)
    return (b.get("tur"), sade(s))


def oncelik(b):
    """Aynı belgenin birden çok kopyası varsa en temiz metni seç."""
    puan = 0
    if b.get("tercih"):  # elle: bu kopyanın metni daha temiz
        puan += 100
    if b["id"].startswith("dx-"):
        puan += 40
    if not b.get("ocr") or b.get("duzeltildi"):
        puan += 20
    # Eşit temizlikteki kopyalardan daha eksiksiz (uzun) metni seç
    return puan + min(len(b.get("govde", "")) / 5000, 15)


def tekillestir(liste):
    gruplar = {}
    for b in liste:
        gruplar.setdefault(baslik_anahtari(b), []).append(b)
    sonuc = {}
    for anahtar, grup in gruplar.items():
        grup.sort(key=oncelik, reverse=True)
        kumeler = [[grup[0]]]
        for b in grup[1:]:
            if str(anahtar[1]).startswith("no:"):
                # Aynı genelge numarası: başlık ya da metin de benzemeli (yanlış numara birleştirmesin)
                import difflib
                for kume in kumeler:
                    if difflib.SequenceMatcher(None, baslik_ozu(b), baslik_ozu(kume[0])).ratio() >= 0.55 \
                            or metin_benzer(b, kume[0]):
                        kume.append(b)
                        break
                else:
                    kumeler.append([b])
            else:
                kumeler[0].append(b)
        for kume in kumeler:
            ana = kume[0]
            for diger in kume[1:]:
                ana.setdefault("eski_kimlikler", []).append((diger["tur"], diger["id"]))
                for alan in ("tarih", "sayi", "rg_tarih", "rg_sayi", "birim", "konu", "etiketler", "kaynak_url"):
                    if diger.get(alan) and not ana.get(alan):
                        ana[alan] = diger[alan]
                if diger.get("kaynak") and diger["kaynak"] != ana.get("kaynak"):
                    ana.setdefault("diger_kaynaklar", []).append(diger["kaynak"])
            sonuc[ana["id"]] = ana
    return sonuc


def sade(s):
    s = unicodedata.normalize("NFC", s or "").casefold().replace("i̇", "i")
    tablo = str.maketrans("çğıöşüâîû", "cgiosuaiu")
    return re.sub(r"[^0-9a-z]+", " ", s.translate(tablo)).strip()


def esini_bul(belgeler, k):
    global _ES_DIZIN
    if _ES_DIZIN is None or _ES_DIZIN[0] != len(belgeler):
        dizin = {}
        for b in belgeler.values():
            dizin.setdefault(baslik_anahtari(b), b)
            if b.get("tur") in ("kanun", "cbk") and b.get("sayi"):
                dizin.setdefault((b["tur"], "no:" + b["sayi"]), b)
        _ES_DIZIN = (len(belgeler), dizin)
    dizin = _ES_DIZIN[1]
    es = dizin.get(baslik_anahtari(k))
    if not es and k.get("tur") in ("kanun", "cbk") and k.get("sayi"):
        es = dizin.get((k["tur"], "no:" + k["sayi"]))
    return es


_ES_DIZIN = None


# ---------------------------------------------------------------- yardımcılar
XML_DISI = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")


def e(s):
    return html.escape(XML_DISI.sub("", str(s or "")), quote=True)


def tarih_tr(iso):
    if not iso:
        return ""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", iso)
    return f"{m.group(3)}.{m.group(2)}.{m.group(1)}" if m else iso


def satir_ici(s):
    s = e(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = s.replace("&lt;small&gt;", "<small>").replace("&lt;/small&gt;", "</small>")
    s = re.sub(r"&lt;sup&gt;(\[\d+\])&lt;/sup&gt;", r"<sup>\1</sup>", s)
    s = re.sub(r"&lt;i&gt;(.+?)&lt;/i&gt;", r"<em>\1</em>", s)
    s = s.replace("&lt;i&gt;", "").replace("&lt;/i&gt;", "")
    s = s.replace("&lt;br&gt;", "<br>")
    return s


def bicim_parcala(s):
    """'**koyu**' ve '<i>italik</i>' işaretli metni (metin, koyu, italik) parçalarına ayırır."""
    parcalar, koyu, italik = [], False, False
    for t in re.split(r"(\*\*|</?i>)", s):
        if t == "**":
            koyu = not koyu
        elif t == "<i>":
            italik = True
        elif t == "</i>":
            italik = False
        elif t:
            parcalar.append((t, koyu, italik))
    return parcalar


def word_ekle(p, s, koyu_hep=False):
    for t, k, i in bicim_parcala(s):
        r = p.add_run(t)
        r.bold = k or koyu_hep
        r.italic = i


def pdf_bicim(s):
    out = []
    for t, k, i in bicim_parcala(s):
        t = html.escape(t, quote=False)
        if i:
            t = f"<i>{t}</i>"
        if k:
            t = f"<b>{t}</b>"
        out.append(t)
    return "".join(out)


# ---------------------------------------------------------------- hizalama kuralı
# Resmî yazı düzeni: kurum başlığı ve büyük harfli başlıklar ortada; Sayı/Konu/İlgi/Ek/Dağıtım
# solda (Sayı satırındaki tarih sağda); kapanış cümlesinden sonraki imza bloğu sağda; gövde iki yana yaslı.
_TARIH = r"\d{1,2}[./]\d{1,2}[./]\d{4}"
_SOL = re.compile(r"^(Sayı|SAYI|Konu|KONU|İlgi|İLGİ|İlgi\s*\(?[a-zA-Z]\)?|Eki?|EKİ?|Ekler|EKLER|Ek\s*-?\s*\d+|EK\s*-?\s*\d+|Dağıtım|DAĞITIM|Gereği|GEREĞİ|Bilgi|BİLGİ)\s*[:：]")
_DAGITIM = re.compile(r"^(Dağıtım|DAĞITIM|Gereği|GEREĞİ|Bilgi|BİLGİ)\s*[:：]?\s*$|^(Dağıtım|DAĞITIM)\s*[:：]")
_KAPANIS = re.compile(r"((arz|rica|arz\s*/\s*rica|rica\s*/\s*arz|arz ve rica)\s+(ederim|ederiz)|(arz|rica) olunur|saygılarımla)", re.I)
_KURUM = re.compile(r"^(T\.\s?C\.?|.{0,70}(BAKANLIĞI|Bakanlığı|MÜDÜRLÜĞÜ|Müdürlüğü|BAŞKANLIĞI|Başkanlığı|VALİLİĞİ|Valiliği|KURUMU|Kurumu|Hastanesi|HASTANESİ|Rektörlüğü|REKTÖRLÜĞÜ))$")
_UNVAN = re.compile(r"^((Prof\.|Doç\.|Dr\.|Uzm\.|Op\.|Av\.|Ecz\.).{0,50}|Bakan( a\.?| V\.)?|Bakan Yard\w+|Vali( a\.?| V\.)?|.{0,45}(Genel Müdür|Başkan|Müdür|Müsteşar|Sekreter|Daire Başkanı)( V\.| a\.| Yardımcısı)?)$")


def _duz(s):
    return " ".join(re.sub(r"\*\*|</?small>|</?sup>|</?i>", "", s).split())


def _buyuk(s):
    harf = [c for c in s if c.isalpha()]
    return len(harf) >= 4 and sum(c.isupper() for c in harf) / len(harf) >= 0.85


def hizalar(bloklar):
    """Her blok için None (iki yana), 'orta', 'sol', 'sag', 'imza' döndürür."""
    sonuc, durum, uzun_goruldu = [], None, False
    for i, blok in enumerate(bloklar):
        if re.match(r"^(#{2,4} |\||---$|\*\*(GEÇİCİ |Geçici |EK |Ek )?(MADDE|Madde))", blok) or blok.startswith("<small>"):
            sonuc.append(None); durum = None if durum == "imza" else durum; continue
        satirlar = [_duz(s) for s in blok.split("\n") if _duz(s)]
        t = " ".join(satirlar)
        kisa = all(len(s) <= 75 for s in satirlar) and len(satirlar) <= 6
        h = None
        if kisa and re.match(r"(?i)^uygun görüşle (arz|arz ve teklif) ederim", satirlar[0]):
            h = "onay"
        elif kisa and any(re.fullmatch(r"O\s?L\s?U\s?R|Olur", x) for x in satirlar):
            h = "olur"
        elif durum in ("onay", "olur") and kisa and len(satirlar) <= 3 and len(t) <= 90 and not _SOL.match(t):
            h = durum
        elif durum == "dagitim" and all(len(x) <= 120 for x in satirlar):
            h = "sol"
        elif _SOL.match(t):
            h = "sol"
            if _DAGITIM.match(t) and i >= len(bloklar) * 0.4:
                durum = "dagitim"
        elif re.fullmatch(_TARIH, t):
            h = "sag"
        elif durum == "imza" and kisa and len(t) <= 160:
            h = "imza"
        elif kisa and (not uzun_goruldu and i < 8 or re.fullmatch(r"T\.\s?C\.?", satirlar[0])) and all(_KURUM.match(s) or _buyuk(s) for s in satirlar):
            # belge başındaki kurum başlığı; ekteki ayrı yazılarda "T.C." ile başlayan başlık da
            h = "orta"
        elif kisa and len(t) <= 110 and any(_buyuk(s) for s in satirlar) and all(_buyuk(s) or re.fullmatch(r"[\d/.\- ]+", s) for s in satirlar) and not t.endswith((":", ";", ",")):
            h = "orta"
        elif kisa and all(_UNVAN.match(s) for s in satirlar) and i >= len(bloklar) * 0.5:
            h = "imza"
            j = len(sonuc) - 1  # hemen önceki kısa ad satırı da imzaya dahil
            if j >= 0 and sonuc[j] is None and len(_duz(bloklar[j])) <= 50 and not _KAPANIS.search(_duz(bloklar[j])):
                sonuc[j] = "imza"
        if h != "sol" and durum == "dagitim":
            durum = None
        if h in ("onay", "olur"):
            durum = h; sonuc.append(h); continue
        if durum in ("onay", "olur"):
            durum = None
        if h is None:
            if len(t) > 120:
                uzun_goruldu = True
            if durum == "imza":
                durum = None
        if h is None and _KAPANIS.search(t[-45:]):
            durum = "imza"
        elif h == "imza" and durum == "imza":
            pass
        elif durum == "imza" and h not in ("imza",):
            durum = "dagitim" if durum == "dagitim" else None
        sonuc.append(h)
    return sonuc


def _sayi_satiri(s):
    """'Sayı: X 26.08.2026' -> (sol, tarih) ya da None."""
    m = re.match(r"^((?:Sayı|SAYI)\s*[:：].*?)[\s*•,-]+(" + _TARIH + r")\s*$", _duz(s))
    return (m.group(1), m.group(2)) if m else None




def satirlara_bol(blok, hz):
    """Hizalı bloklarda Sayı/Konu ve imza unvanlarını ayrı satırlara böler."""
    satirlar = [x for x in blok.split("\n") if x.strip()]
    if hz == "sol":
        yeni = []
        for x in satirlar:
            m = re.match(r"^((?:Sayı|SAYI)\s*[:：].*?)\s+((?:Konu|KONU)\s*[:：].*)$", _duz(x))
            if m:
                sayi, konu = m.group(1), m.group(2)
                t = re.search(r"[\s*•,-]+(" + _TARIH + r")\s*$", konu)
                if t:
                    konu, sayi = konu[:t.start()], sayi + " " + t.group(1)
                yeni += [sayi, konu]
            else:
                yeni.append(x)
        return yeni
    if hz == "imza":
        yeni = []
        for x in satirlar:
            yeni += [y for y in re.split(r"\s+(?=(?:Bakan a\.?|Bakan Yardımcısı|Bakan|Müsteşar|Vali a\.?|Vali V\.)(?:\s|$))", _duz(x)) if y]
        return yeni
    return satirlar


_SIRA = r"(?:BİRİNCİ|İKİNCİ|ÜÇÜNCÜ|DÖRDÜNCÜ|BEŞİNCİ|ALTINCI|YEDİNCİ|SEKİZİNCİ|DOKUZUNCU|ONUNCU|ON\s?BİRİNCİ|ON\s?İKİNCİ|ON\s?ÜÇÜNCÜ|ON\s?DÖRDÜNCÜ|ON\s?BEŞİNCİ|ON\s?ALTINCI|ON\s?YEDİNCİ|ON\s?SEKİZİNCİ|ON\s?DOKUZUNCU|YİRMİNCİ)"
BOLUM_TEK = re.compile(r"^(#{1,4} |\*\*)?\s*(" + _SIRA + r"\s+(?:BÖLÜM|KISIM|KİTAP|BAP|FASIL))\s*(?:\*\*)?\s*[-–:.]?\s*(\S.*?)(?:\*\*)?$")


BOLUM_GOMULU = re.compile(r"\*\*([^*]*?)\s*\b(" + _SIRA + r"\s+(?:BÖLÜM|KISIM))\s+([^*]+?)\s+((?:GEÇİCİ |EK )?(?:MADDE|Madde)\s*\d+[/A-Za-z]*\s*[-–—:]?)\*\*\s*(.*)$", re.S)
_BAG = {"ve", "ile", "veya", "ya", "da", "de", "için", "ilişkin", "dair", "ait", "hakkında", "göre", "olan", "bazı", "diğer", "çeşitli", "son"}


def _ad_baslik_bol(ad):
    """'Başlangıç Hükümleri Amaç' -> ('Başlangıç Hükümleri', 'Amaç'); madde başlığı son büyük harfli sözcükten başlar."""
    w = ad.split()
    for i in range(len(w) - 1, 0, -1):
        if (w[i][:1].isupper() and all(x[:1].islower() or x.lower() in _BAG or not x[:1].isalpha() for x in w[i + 1:])
                and w[i - 1].lower() not in ("ve", "ile", "veya")):
            return " ".join(w[:i]), " ".join(w[i:])
    return None

def bloklari_duzenle(govde):
    """Başlık satırına yapışık metni ayırır; MADDE'den hemen önceki kısa başlığı koyu madde başlığı yapar; '# ' -> '## '."""
    # tek paragrafa yığılmış maddeler: satır ortasındaki "**… MADDE n –**" ve "**… BÖLÜM …**" yeni paragraf başlatır
    govde = re.sub(r"(?<=\S) +\*\*(?=[^*\n]{0,160}?(?:\b(?:MADDE|Madde)\s*\d+[/A-Za-z]*\s*[-–—:]?|" + _SIRA + r"\s+(?:BÖLÜM|KISIM)\b[^*\n]*)\*\*)", "\n\n**", govde)
    out = []
    for blok in re.split(r"\n{2,}", govde.strip()):
        satirlar = blok.strip().split("\n")
        if len(satirlar) > 1 and re.match(r"^#{1,4} ", satirlar[0].strip()):
            out.extend(x.strip() for x in satirlar if x.strip())
        else:
            out.append(blok.strip())
    for j, b in enumerate(out):
        if re.match(r"^# ", b):
            out[j] = "#" + b
    # "BİRİNCİ BÖLÜM Başlangıç Hükümleri" -> bölüm numarası ve adı ayrı satırlarda (mevzuat.gov.tr düzeni)
    ayrik = []
    for b in out:
        m = BOLUM_TEK.match(b) if "\n" not in b else None
        if m and not re.search(r"\b(MADDE|Madde)\s*\d", m.group(3)) and len(m.group(3)) <= 250:
            ayrik += ["## " + m.group(2), "### " + m.group(3).strip().strip("*").strip()]
        else:
            ayrik.append(b)
    out = ayrik
    # "**ADI YÖNETMELİĞİ BİRİNCİ BÖLÜM Başlangıç Hükümleri Amaç MADDE 1-** metin" -> ayrı satırlar
    ayrik = []
    for b in out:
        kalan = b
        while True:
            m = BOLUM_GOMULU.search(kalan) if "\n" not in kalan else None
            if not m:
                ayrik.append(kalan); break
            once = kalan[:m.start()].strip()
            if once: ayrik.append(once)
            if m.group(1).strip(): ayrik.append("## " + m.group(1).strip())
            ayrik.append("## " + m.group(2))
            iki = _ad_baslik_bol(m.group(3))
            if iki:
                ayrik += ["### " + iki[0], "**" + iki[1] + "**"]
            else:
                ayrik.append("### " + m.group(3).strip())
            kalan = "**" + m.group(4).strip() + "** " + m.group(5).strip()
    out = ayrik
    # tek başına kalan "GEÇİCİ" / "EK" sözcüğü sonraki MADDE etiketine katılır
    ayrik = []
    for b in out:
        if ayrik and re.fullmatch(r"(?:\*\*)?(GEÇİCİ|Geçici|EK|Ek)(?:\*\*)?", ayrik[-1].strip()) and re.match(r"^\*\*(MADDE|Madde)\s*\d", b):
            ayrik[-1] = "**" + re.sub(r"\*", "", ayrik[-1]).strip() + " " + b[2:]
        else:
            ayrik.append(b)
    out = ayrik
    # "**Kapsam MADDE 2 –** metin" -> "**Kapsam**" + "**MADDE 2 –** metin"
    ayrik = []
    for b in out:
        m = re.match(r"^\*\*([A-ZÇĞİÖŞÜ][^*\n]{1,80}?)\s+((?:GEÇİCİ |Geçici |EK |Ek )?(?:MADDE|Madde)\s*\d+[/A-Za-z]*\s*[-–—:]?)\*\*(.*)$", b, re.S)
        if m and not re.search(r"(BÖLÜM|KISIM)", m.group(1)) and not re.fullmatch(r"(GEÇİCİ|Geçici|EK|Ek|MÜKERRER|Mükerrer)", m.group(1).strip()):
            ayrik += ["**" + m.group(1).strip() + "**", "**" + m.group(2) + "**" + m.group(3)]
        else:
            ayrik.append(b)
    out = ayrik
    # Konu'nun ayrı paragrafa düşmüş devam satırı ve İlgi'nin b), c) … maddeleri kendi bloğuna katılır
    birlesik = []
    for b in out:
        if birlesik:
            onc = birlesik[-1]; ilk = re.sub(r"\*\*", "", onc.split("\n")[0])
            sade = re.sub(r"\*\*", "", b)
            if (re.match(r"^(Konu|KONU)\s*[:：]", re.sub(r"\*\*", "", onc.split("\n")[-1])) and "\n" not in b
                    and len(sade) <= 60 and not re.search(r"[:：]", sade) and not _buyuk(sade)):
                birlesik[-1] = onc + "\n" + b; continue
            if (re.match(r"^(İlgi|İLGİ)\s*[:：]", ilk) and re.match(r"^[b-hçğ]\)\s", sade)
                    and len(sade) <= 300 and re.search(r"tarih|sayılı|yazı|dilekçe|Genelge|Yönetmelik|Kanun|tutanak", sade)):
                birlesik[-1] = onc + "\n" + b; continue
        birlesik.append(b)
    out = birlesik
    for j, b in enumerate(out[:-1]):
        m = re.match(r"^#{3,4} (.{1,90})$", b)
        if m and re.match(r"^\*\*(?:GEÇİCİ |Geçici |EK |Ek )?(?:MADDE|Madde)", out[j + 1]) and not re.search(r"BÖLÜM|KISIM", m.group(1)):
            out[j] = "**" + m.group(1).strip().strip("*") + "**"
    return "\n\n".join(out)



KUNYE_ETIKET = re.compile(r"^(?:\*\*)?(Sayı|SAYI|Konu|KONU|İlgi|İLGİ|Tarih|TARİH)(?:\*\*)?\s*[:：]\s*(?:\*\*)?\s*(.*)$")


def kunye_html(satirlar):
    """Sayı/Konu/İlgi satırlarını etiket | : | değer düzeninde yazar; devam satırları değerin hizasından sürer (Yön. md. 13, 15)."""
    rows = []
    for s in satirlar:
        t = s.strip()
        m = KUNYE_ETIKET.match(t)
        if m:
            rows.append([m.group(1), [m.group(2)]])
        elif rows and rows[-1][0] and not re.match(r"^\S[^:]{0,15}:", _duz(t)):
            rows[-1][1].append(t)
        else:
            rows.append([None, [t]])
    if not any(r[0] for r in rows):
        return None
    out = []
    for et, vals in rows:
        if et is None:
            out.append(f'<span class="kunye-duz">{satir_ici(vals[0])}</span>')
            continue
        deger = "<br>".join(satir_ici(v) for v in vals)
        if et.lower().startswith("say") and len(vals) == 1:
            ss = _sayi_satiri(f"Sayı: {vals[0]}")
            if ss:
                no = re.sub(r"^Sayı\s*:\s*", "", ss[0])
                deger = f'<span class="sayi-satir"><span>{satir_ici(no)}</span><span>{satir_ici(ss[1])}</span></span>'
        out.append(f'<span class="kunye"><span class="et">{e(et)}</span><span>:</span><span class="dg">{deger}</span></span>')
    return "".join(out)


def sol_sinif(blok):
    t = _duz(blok.split("\n")[0])
    if re.match(r"^(İlgi|İLGİ)\b", t): return " ilgi"
    if re.match(r"^(Ekler|EKLER|Ek|EK)\b", t): return " ek"
    if re.match(r"^(Dağıtım|DAĞITIM)\b", t): return " dagitim"
    return ""

def md_html(govde):
    parcalar, sayac = [], 0
    bloklar = [b.strip() for b in re.split(r"\n{2,}", bloklari_duzenle(govde)) if b.strip()]
    hiza = hizalar(bloklar)
    for blok, hz in zip(bloklar, hiza):
        if blok == "---":
            parcalar.append("<hr>")
            continue
        satirlar = [s.strip() for s in blok.split("\n")]
        if len(satirlar) >= 1 and all(s.startswith("|") for s in satirlar):
            govde_satir = [s for s in satirlar if not re.fullmatch(r"\|[\s:|-]+\|?", s)]
            ham = [[h.strip() for h in s.strip("|").split("|")] for s in govde_satir]
            # "^^" içeren hücre üstteki hücreyle birleşir (rowspan)
            span = [[1] * len(r) for r in ham]
            for i, r in enumerate(ham):
                for j, h in enumerate(r):
                    if h == "^^":
                        k = i - 1
                        while k >= 0 and (j >= len(ham[k]) or ham[k][j] == "^^"):
                            k -= 1
                        if k >= 0:
                            span[k][j] += 1
            satir_html = []
            for i, r in enumerate(ham):
                hucre = "".join((f'<td rowspan="{span[i][j]}">' if span[i][j] > 1 else "<td>") + satir_ici(h) + "</td>"
                                for j, h in enumerate(r) if h != "^^")
                satir_html.append(f"<tr>{hucre}</tr>")
            parcalar.append('<div class="tablo-kap"><table class="metin-tablo">' + "".join(satir_html) + "</table></div>")
            continue
        m = re.match(r"^(#{2,4}) (.*)$", blok, re.S)
        if m:
            seviye = len(m.group(1))
            parcalar.append(f"<h{seviye}>" + "<br>".join(satir_ici(x) for x in re.split(r"\s+#{2,4}\s+", m.group(2))) + f"</h{seviye}>")
            continue
        if blok.startswith("**") and re.match(r"^\*\*(?:GEÇİCİ |Geçici |EK |Ek )?(?:MADDE|Madde)", blok):
            sayac += 1
            no = re.search(r"\d+[/A-Za-z]*", blok)
            kimlik = "madde-" + (no.group(0).lower().replace("/", "-") if no else str(sayac))
            if "geçici" in blok[:15].lower():
                kimlik = "gecici-" + kimlik
            parcalar.append(f'<p class="madde" id="{kimlik}">{satir_ici(blok)}</p>')
            continue
        satir_html = []
        for s in (satirlara_bol(blok, hz) if hz else blok.split("\n")):
            ss = _sayi_satiri(s)
            satir_html.append(f'<span class="sayi-satir"><span>{satir_ici(ss[0])}</span><span>{satir_ici(ss[1])}</span></span>' if ss else satir_ici(s))
        sinif = f' class="h-{hz}{sol_sinif(blok) if hz == "sol" else ""}"' if hz else ""
        kh = kunye_html(satirlara_bol(blok, hz)) if hz == "sol" else None
        parcalar.append(f"<p{sinif}>" + (kh if kh else "<br>".join(satir_html)) + "</p>")
    # ardışık imza paragraflarını tek blokta topla
    html_metin = "\n".join(parcalar)
    for sinif in ("imza", "onay", "olur"):
        html_metin = re.sub(r'((?:<p class="h-%s">.*?</p>\n?)+)' % sinif, lambda m, c=sinif: f'<div class="{c}">' + m.group(1).replace(f' class="h-{c}"', '') + '</div>\n', html_metin)
    # Gereği / Bilgi bloklarını PDF'teki gibi yan yana göster
    html_metin = re.sub(r'(<p class="h-sol">(?:<strong>)?(?:Gereği|GEREĞİ)\s*:.*?</p>)\n(<p class="h-sol">(?:<strong>)?(?:Bilgi|BİLGİ)\s*:.*?</p>)',
                        r'<div class="iki-sutun">\1\n\2</div>', html_metin)
    return html_metin


def duz_bloklar(govde):
    """Word/PDF üretimi için (tip, metin) listesi."""
    govde = XML_DISI.sub("", govde)
    bloklar = [b.strip() for b in re.split(r"\n{2,}", bloklari_duzenle(govde)) if b.strip()]
    for blok, hz in zip(bloklar, hizalar(bloklar)):
        if hz:
            for s in satirlara_bol(blok, hz):
                ss = _sayi_satiri(s)
                yield ("p-sayi", ss) if ss else ("p-" + hz, _duz(s))
            continue
        if blok == "---":
            yield ("hr", "")
        elif blok.startswith("**Dipnotlar**"):
            yield ("h4", "Dipnotlar")
        elif re.match(r"^#{2,4} ", blok):
            for x in re.split(r"\s+#{2,4}\s+", blok.split(" ", 1)[1]):
                yield ("h" + str(len(blok.split(" ")[0])), x)
        elif blok.startswith("<small>"):
            yield ("dipnot", re.sub(r"</?small>", "", blok))
        else:
            blok = re.sub(r"</?sup>", "", blok)
            m = re.match(r"^\*\*(.+?)\*\*\s*(.*)$", blok, re.S)
            if m:
                yield ("madde", (m.group(1), m.group(2)))
            else:
                yield ("p", blok)


def kunye(b):
    satirlar = [("Mevzuat Türü", TUR_TEKIL[b["tur"]])]
    if b.get("tarih"):
        satirlar.append(("Tarih", tarih_tr(b["tarih"])))
    if b.get("sayi"):
        satirlar.append(("Sayı / Numara", b["sayi"]))
    if b.get("rg_tarih") or b.get("rg_sayi"):
        satirlar.append(("Resmî Gazete", " – ".join(x for x in [tarih_tr(b.get("rg_tarih")), b.get("rg_sayi") and "Sayı: " + b["rg_sayi"]] if x)))
    if b.get("birim"):
        satirlar.append(("Yayımlayan Birim", b["birim"]))
    if b.get("durum"):
        satirlar.append(("Durum", b["durum"].capitalize()))
    if b.get("kaynak"):
        satirlar.append(("Kaynak", b["kaynak"]))
    for k in b.get("diger_kaynaklar", []):
        satirlar.append(("Diğer kaynak", k))
    if b.get("not"):
        satirlar.append(("Not", b["not"]))
    if b.get("ocr"):
        satirlar.append(("Aktarım", "Taranmış sayfalardan OCR ile aktarılmıştır; yazım hataları içerebilir."))
    return satirlar


# ---------------------------------------------------------------- şablon
def sayfa(baslik, icerik, kok="", aciklama=""):
    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(baslik)} | {SITE_ADI}</title>
<meta name="description" content="{e(aciklama or 'Sağlık mevzuatı: kanun, yönetmelik, yönerge, genelge ve Sağlık Bakanlığı yazışmaları')}">
<link rel="stylesheet" href="{kok}assets/stil.css?v={STIL_SURUM}">
<link rel="icon" href="{kok}assets/simge.svg" type="image/svg+xml">
</head>
<body>
<header class="ust">
  <div class="kap ust-ic">
    <a class="logo" href="{kok}index.html"><img src="{kok}assets/simge.svg" alt="" width="40" height="40"><span><strong>Canlı Sağlık Mevzuatı</strong><small>Sağlık mevzuatı bilgi sistemi</small></span></a>
    <nav class="menu">
      <a href="{kok}index.html">Ana Sayfa</a>
      <a href="{kok}ara.html">Detaylı Arama</a>
      <a href="{kok}hakkinda.html">Hakkında</a>
    </nav>
  </div>
</header>
<main class="kap">
{icerik}
</main>
<footer class="alt">
  <div class="kap">
    <p><strong>{SITE_ADI}</strong> — sağlıkla ilgili kanun, yönetmelik, yönerge, genelge ve Sağlık Bakanlığı yazışmalarını tek yerde toplar.</p>
    <p class="uyari">Bu site resmî bir kaynak değildir. Metinler derlenmiş kitaplardan ve resmî sitelerden aktarılmıştır; hukuki işlemlerde Resmî Gazete ve ilgili kurumun yayımladığı metin esas alınmalıdır.</p>
    <p class="ithaf"><em>Her zaman ufkumu açan Prof. Dr. Cemil Özcan'a en derin saygılarımla.</em></p>
  </div>
</footer>
<script src="{kok}assets/ara.js?v={ARA_SURUM}" defer></script>
</body>
</html>
"""


def belge_sayfasi(b):
    kok = "../../"
    k = "".join(f"<tr><th>{e(a)}</th><td>{e(v)}</td></tr>" for a, v in kunye(b))
    kaynaklar = [u for u in [b.get("kaynak_url")] + list(b.get("ek_kaynaklar") or []) if u]
    kaynaklar = list(dict.fromkeys(kaynaklar))
    if kaynaklar:
        baglar = "<br>".join(f'<a href="{e(u)}" rel="noopener" target="_blank">{e(u)}</a>' for u in kaynaklar)
        k += f'<tr><th>Resmî Kaynak</th><td>{baglar}</td></tr>'
    if b.get("degistirdigi"):
        satir = []
        for d in b["degistirdigi"]:
            ad = e(d.get("ad", ""))
            if d.get("id"):
                tur_ = d.get("tur") or b["tur"]
                ad = f'<a href="{kok}mevzuat/{e(tur_)}/{e(d["id"])}.html">{ad}</a>'
            if d.get("url"):
                ad += f' — <a href="{e(d["url"])}" rel="noopener" target="_blank">mevzuat.gov.tr</a>'
            satir.append(f"<li>{ad}</li>")
        k += f'<tr><th>Değiştirdiği Mevzuat</th><td><ul>{"".join(satir)}</ul></td></tr>'
    if b.get("degisiklikler"):
        lis = "".join(f"<li>{e(tarih_tr(d.get('rg_tarih')))} {('RG ' + e(d.get('rg_sayi'))) if d.get('rg_sayi') else ''} {e(d.get('aciklama'))}</li>" for d in b["degisiklikler"])
        k += f"<tr><th>Değişiklikler</th><td><ul>{lis}</ul></td></tr>"
    etiket = "".join(f'<a class="etiket" href="{kok}ara.html?q={e(t)}">{e(t)}</a>' for t in b.get("etiketler", []))
    if b["tam_metin"]:
        indir = f"""<div class="indir">
  <a class="dugme word" href="{e(b['id'])}.docx" download>Word olarak indir</a>
  <a class="dugme pdf" href="{e(b['id'])}.pdf" download>PDF olarak indir</a>
  <button class="dugme yazdir" onclick="window.print()">Yazdır</button>
</div>"""
        govde = f'<article class="metin" id="metin">{md_html(b["govde"])}</article>'
        ara = '<div class="metin-ara"><input type="search" id="metinde-ara" placeholder="Metin içinde ara…" aria-label="Metin içinde ara"><span id="metinde-sonuc"></span></div>'
    else:
        indir = ""
        if b.get("kaynak_url"):
            indir = f'<div class="indir"><a class="dugme" href="{e(b["kaynak_url"])}" target="_blank" rel="noopener">Resmî kaynakta görüntüle</a></div>'
        govde = '<p class="bilgi">Bu mevzuatın tam metni henüz sisteme eklenmedi. Künye bilgileri ve resmî kaynağa bağlantı aşağıdadır.</p>'
        ara = ""
    icerik = f"""<nav class="yol"><a href="{kok}index.html">Ana Sayfa</a> › <a href="{kok}tur/{grup(b['tur'])}.html">{e(TUR_ADLARI[grup(b['tur'])])}</a></nav>
<h1 class="belge-baslik">{e(b['baslik'])}</h1>
{indir}
<table class="kunye">{k}</table>
<div class="etiketler">{etiket}</div>
{ara}
{govde}"""
    return sayfa(b["baslik"], icerik, kok, b.get("konu", ""))


def sirala_anahtar(b):
    return (b.get("son_degisiklik") or b.get("rg_tarih") or b.get("tarih") or "0000")


RG_TURLERI = {"kanun", "khk", "cbk", "yonetmelik", "teblig", "tuzuk", "bkk"}


def tablo(belgeler, kok):
    # Resmî Gazete sütunu yalnız Resmî Gazete'de yayımlanan türlerin listelerinde görünür (tarih / sayı);
    # tüzük ve yönetmelik listelerinde Sayı sütunu gösterilmez
    rg_sutun = any(b["tur"] in RG_TURLERI and b.get("rg_tarih") for b in belgeler)
    sayi_sutun = not belgeler or any(b["tur"] not in ("tuzuk", "yonetmelik") for b in belgeler)
    sd_sutun = any(b["tur"] in SD_TURLERI for b in belgeler)
    satirlar = []
    for b in belgeler:
        isaret = "" if b["tam_metin"] else ' <span class="rozet">künye</span>'
        siralama_tarihi = b.get("tarih") or b.get("rg_tarih") or ""
        rg_metin = " / ".join(x for x in [tarih_tr(b.get("rg_tarih")), b.get("rg_sayi")] if x)
        rg = f"<td>{e(rg_metin)}</td>" if rg_sutun else ""
        sayi = f'<td>{e(b.get("sayi"))}</td>' if sayi_sutun else ""
        sd = b.get("son_degisiklik", "")
        sdh = f"<td>{e(tarih_tr(sd))}</td>" if sd_sutun else ""
        satirlar.append(
            f'<tr data-ad="{e(sade(b["baslik"]))}" data-tarih="{e(siralama_tarihi)}" data-son="{e(sd)}">'
            f'<td><a href="{kok}mevzuat/{b["tur"]}/{e(b["id"])}.html">{e(b["baslik"])}</a>{isaret}</td>'
            f'<td>{e(TUR_TEKIL[b["tur"]])}</td><td>{e(tarih_tr(b.get("tarih")))}</td>{sdh}{sayi}{rg}</tr>')
    bas = ("<th>Mevzuat Adı</th><th>Tür</th><th>Tarih</th>" + ('<th data-kolon="son">Son Değişiklik</th>' if sd_sutun else "")
           + ("<th>Sayı</th>" if sayi_sutun else "") + ("<th>Resmî Gazete</th>" if rg_sutun else ""))
    return (f'<table class="liste"><thead><tr>{bas}</tr></thead><tbody>'
            + "".join(satirlar) + "</tbody></table>")


def ana_sayfa(belgeler):
    sayac = {t: 0 for t in TUR_ADLARI}
    for b in belgeler.values():
        sayac[grup(b["tur"])] += 1
    kartlar = "".join(
        f'<a class="kart" href="tur/{t}.html"><span class="sayi">{sayac[t]}</span><span>{e(ad)}</span></a>'
        for t, ad in TUR_ADLARI.items() if sayac[t])
    son = sorted((b for b in belgeler.values() if b.get("rg_tarih") or b.get("tarih")), key=sirala_anahtar, reverse=True)[:15]
    tam = sum(1 for b in belgeler.values() if b["tam_metin"])
    icerik = f"""<section class="kahraman">
  <h1>Sağlık mevzuatına tek noktadan ulaşın</h1>
  <p>Kanun, Cumhurbaşkanlığı kararnamesi, yönetmelik, yönerge, genelge ve Sağlık Bakanlığı yazışmaları. Toplam <strong>{len(belgeler)}</strong> kayıt, <strong>{tam}</strong> tam metin.</p>
  <form class="ana-ara" action="ara.html" method="get">
    <input type="search" name="q" placeholder="Mevzuat adı, sayı veya metin içinde ara…" aria-label="Ara" autofocus>
    <button type="submit">Ara</button>
  </form>
</section>
<section><h2>Mevzuat türleri</h2><div class="kartlar">{kartlar}</div></section>
<section><h2>Son düzenlemeler</h2>{tablo(son, "")}</section>"""
    return sayfa("Ana Sayfa", icerik, "")


def tur_sayfasi(tur, belgeler):
    liste = sorted((b for b in belgeler.values() if grup(b["tur"]) == tur), key=lambda b: sade(b["baslik"]))
    sd_secenek = ('<option value="son-yeni">Son değişikliğe göre (yeniden eskiye)</option><option value="son-eski">Son değişikliğe göre (eskiden yeniye)</option>'
                  if any(b["tur"] in SD_TURLERI for b in liste) else "")
    icerik = f"""<nav class="yol"><a href="../index.html">Ana Sayfa</a> › {e(TUR_ADLARI[tur])}</nav>
<h1>{e(TUR_ADLARI[tur])} <small>({len(liste)})</small></h1>
<div class="metin-ara"><input type="search" id="liste-suz" placeholder="Bu listede süz…" aria-label="Listede süz">
<label class="sirala">Sırala <select id="liste-sirala" aria-label="Sıralama">
<option value="ad">Ada göre (A–Z)</option><option value="yeni">Tarihe göre (yeniden eskiye)</option><option value="eski">Tarihe göre (eskiden yeniye)</option>{sd_secenek}
</select></label></div>
{tablo(liste, "../")}"""
    return sayfa(TUR_ADLARI[tur], icerik, "../")


def ara_sayfasi():
    turler = "".join(f'<label><input type="checkbox" name="tur" value="{t}" checked> {e(ad)}</label>' for t, ad in TUR_ADLARI.items() if t not in GRUP)
    icerik = f"""<nav class="yol"><a href="index.html">Ana Sayfa</a> › Detaylı Arama</nav>
<h1>Detaylı Arama</h1>
<form id="arama-formu" class="detayli">
  <div class="satir"><input type="search" id="q" name="q" placeholder="Aranacak ifade" aria-label="Aranacak ifade">
  <button type="submit">Ara</button></div>
  <div class="satir secenek">
    <label><input type="radio" name="kapsam" value="baslik" checked> Mevzuat adında</label>
    <label><input type="radio" name="kapsam" value="metin"> Tam metinde</label>
    <label>Sayı <input type="text" id="sayi" size="10"></label>
    <label>Yıl <input type="number" id="yil1" min="1900" max="2100" placeholder="başlangıç"> – <input type="number" id="yil2" min="1900" max="2100" placeholder="bitiş"></label>
  </div>
  <fieldset class="turler"><legend>Mevzuat türü</legend>{turler}</fieldset>
  <div class="satir secenek"><label class="sirala">Sırala <select id="sonuc-sirala" aria-label="Sonuç sıralaması">
  <option value="yeni">Tarihe göre (yeniden eskiye)</option><option value="eski">Tarihe göre (eskiden yeniye)</option><option value="ad">Ada göre (A–Z)</option>
  </select></label></div>
</form>
<p id="sonuc-bilgi"></p>
<div id="sonuclar"></div>"""
    return sayfa("Detaylı Arama", icerik, "")


def hakkinda_sayfasi(belgeler):
    kaynaklar = sorted({b.get("kaynak", "").split(", s.")[0] for b in belgeler.values() if b.get("kaynak")})
    lis = "".join(f"<li>{e(k)}</li>" for k in kaynaklar if k)
    icerik = f"""<h1>Hakkında</h1>
<p class="ithaf-buyuk"><em>Her zaman ufkumu açan Prof. Dr. Cemil Özcan'a en derin saygılarımla.</em></p>
<p>Siteyi düzenleyen: <strong>Mithat Temizer</strong></p>
<p>Canlı Sağlık Mevzuatı, mevzuat.gov.tr örneğinde olduğu gibi sağlık alanındaki düzenlemeleri tek yerde toplamayı amaçlar. Resmî Gazete'de yayımlanan kanun ve yönetmeliklerin yanında, Resmî Gazete'de yayımlanmadığı için ulaşılması güç olan yönerge, genelge ve Sağlık Bakanlığı yazışmalarını da içerir.</p>
<p>Her tam metinli belge Word (.docx) ve PDF olarak indirilebilir. Tam metni henüz eklenmemiş kayıtlarda künye ve resmî kaynağa bağlantı yer alır.</p>
<h2>Kaynaklar</h2><ul>{lis}<li>mevzuat.gov.tr, saglik.gov.tr ve resmigazete.gov.tr</li></ul>
<h2>Uyarı</h2><p>Metinler basılı derlemelerden otomatik olarak aktarılmıştır ve aktarım hataları içerebilir. Güncel ve bağlayıcı metin için Resmî Gazete ve ilgili kurumun yayını esas alınmalıdır. Hata bildirimi için GitHub deposunda konu (issue) açabilirsiniz.</p>
<p class="kucuk">Son güncelleme: {dt.date.today().strftime('%d.%m.%Y')}</p>"""
    return sayfa("Hakkında", icerik, "")


# ---------------------------------------------------------------- Word / PDF
def word_uret(b, hedef):
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
    from docx.shared import Pt, RGBColor

    d = Document()
    st = d.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = Pt(11)
    for s in d.sections:
        s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Pt(64)
    p = d.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(b["baslik"].upper())
    r.bold = True
    r.font.size = Pt(13)
    t = d.add_table(rows=0, cols=2)
    t.style = "Table Grid"
    for a, v in kunye(b):
        h = t.add_row().cells
        h[0].text, h[1].text = a, v
        for c in h:
            for pp in c.paragraphs:
                for rr in pp.runs:
                    rr.font.size = Pt(9)
        h[0].paragraphs[0].runs[0].bold = True
    d.add_paragraph()
    for tip, metin in duz_bloklar(b["govde"]):
        if tip == "hr":
            continue
        if tip in ("h2", "h3"):
            p = d.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run(metin).bold = True
        elif tip == "h4":
            p = d.add_paragraph()
            p.add_run(metin).bold = True
            p.paragraph_format.space_after = Pt(0)
        elif tip == "madde":
            p = d.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            word_ekle(p, metin[0] + " ", koyu_hep=True)
            word_ekle(p, metin[1])
            p.paragraph_format.first_line_indent = Pt(28)
        elif tip == "dipnot":
            p = d.add_paragraph()
            r = p.add_run(metin)
            r.font.size = Pt(8)
            r.font.color.rgb = RGBColor(0x44, 0x44, 0x44)
        elif tip == "p-sayi":
            p = d.add_paragraph()
            p.paragraph_format.tab_stops.add_tab_stop(d.sections[0].page_width - d.sections[0].left_margin - d.sections[0].right_margin, WD_TAB_ALIGNMENT.RIGHT)
            p.add_run(metin[0] + "\t" + metin[1])
            p.paragraph_format.space_after = Pt(0)
        elif tip.startswith("p-"):
            p = d.add_paragraph(metin)
            p.alignment = {"p-orta": WD_ALIGN_PARAGRAPH.CENTER, "p-sag": WD_ALIGN_PARAGRAPH.RIGHT, "p-imza": WD_ALIGN_PARAGRAPH.RIGHT, "p-olur": WD_ALIGN_PARAGRAPH.CENTER}.get(tip, WD_ALIGN_PARAGRAPH.LEFT)
            p.paragraph_format.space_after = Pt(0) if tip in ("p-sol", "p-imza", "p-orta", "p-onay", "p-olur") else p.paragraph_format.space_after
        else:
            p = d.add_paragraph()
            word_ekle(p, metin)
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.first_line_indent = Pt(28)
    p = d.add_paragraph()
    r = p.add_run(f"Bu belge {SITE_ADI} sitesinden alınmıştır. Resmî metin için Resmî Gazete ve ilgili kurum yayını esas alınmalıdır.")
    r.italic = True
    r.font.size = Pt(8)
    d.core_properties.title = b["baslik"]
    d.save(hedef)


_FONT = None


def font_kaydet():
    global _FONT
    if _FONT:
        return _FONT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.fonts import addMapping
    L = "/usr/share/fonts/truetype/liberation/LiberationSerif-"
    T = "/System/Library/Fonts/Supplemental/Times New Roman"
    J = "/usr/share/fonts/truetype/dejavu/DejaVuSerif"
    adaylar = [
        (L + "Regular.ttf", L + "Bold.ttf", L + "Italic.ttf", L + "BoldItalic.ttf"),
        (T + ".ttf", T + " Bold.ttf", T + " Italic.ttf", T + " Bold Italic.ttf"),
        (J + ".ttf", J + "-Bold.ttf", J + "-Italic.ttf", J + "-BoldItalic.ttf"),
        (J + ".ttf", J + "-Bold.ttf", J + ".ttf", J + "-Bold.ttf"),
    ]
    for normal, kalin, italik, kalin_italik in adaylar:
        if all(Path(x).exists() for x in (normal, kalin, italik, kalin_italik)):
            pdfmetrics.registerFont(TTFont("Govde", normal))
            pdfmetrics.registerFont(TTFont("Govde-Kalin", kalin))
            pdfmetrics.registerFont(TTFont("Govde-Italik", italik))
            pdfmetrics.registerFont(TTFont("Govde-KalinItalik", kalin_italik))
            addMapping("Govde", 0, 0, "Govde")
            addMapping("Govde", 1, 0, "Govde-Kalin")
            addMapping("Govde", 0, 1, "Govde-Italik")
            addMapping("Govde", 1, 1, "Govde-KalinItalik")
            _FONT = "Govde"
            return _FONT
    raise SystemExit("Türkçe karakter destekli bir TTF yazı tipi bulunamadı (Liberation veya DejaVu kurun).")


def pdf_uret(b, hedef):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, HRFlowable

    f = font_kaydet()
    duz = ParagraphStyle("g0", fontName=f, fontSize=10.5, leading=14, alignment=TA_JUSTIFY, spaceAfter=5)
    govde = ParagraphStyle("g", parent=duz, firstLineIndent=1.25 * cm, spaceAfter=0)
    baslik = ParagraphStyle("b", parent=duz, fontName=f + "-Kalin", fontSize=13, leading=17, alignment=TA_CENTER, spaceAfter=10)
    ara = ParagraphStyle("a", parent=duz, fontName=f + "-Kalin", alignment=TA_CENTER, spaceBefore=6)
    alt = ParagraphStyle("h4", parent=duz, fontName=f + "-Kalin", spaceAfter=1, spaceBefore=4)
    dip = ParagraphStyle("d", parent=duz, fontSize=8, leading=10, textColor=colors.HexColor("#444444"))
    kucuk = ParagraphStyle("k", parent=duz, fontSize=8.5, leading=11, alignment=0)
    solst = ParagraphStyle("sol", parent=duz, alignment=0, spaceAfter=1)
    ortast = ParagraphStyle("orta", parent=duz, alignment=TA_CENTER, spaceAfter=1)
    sagst = ParagraphStyle("sag", parent=duz, alignment=2, spaceAfter=1)
    imzast = ParagraphStyle("imza", parent=duz, alignment=TA_CENTER, leftIndent=9 * cm, spaceAfter=0)
    onayst = ParagraphStyle("onay", parent=duz, alignment=TA_CENTER, rightIndent=9 * cm, spaceAfter=0)
    olurst = ParagraphStyle("olur", parent=duz, alignment=TA_CENTER, spaceAfter=0)

    def x(s):
        return html.escape(s, quote=False)

    akis = [Paragraph(x(b["baslik"].upper()), baslik)]
    t = Table([[Paragraph("<b>" + x(a) + "</b>", kucuk), Paragraph(x(v), kucuk)] for a, v in kunye(b)], colWidths=[4 * cm, 12.5 * cm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
                           ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2f7")),
                           ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    akis += [t, Spacer(1, 10)]
    onceki = None; hitap = False; ilgi_son = False
    for tip, metin in duz_bloklar(b["govde"]):
        SATIR = 14  # 1 satır (10,5 pt yazı, 14 pt satır aralığı)
        IMZALAR = ("p-imza", "p-onay", "p-olur")
        if onceki is not None and tip in IMZALAR and onceki not in IMZALAR:
            akis.append(Spacer(1, 3 * SATIR))
        elif onceki is not None and (tip in IMZALAR or onceki in IMZALAR) and tip != onceki:
            akis.append(Spacer(1, 2 * SATIR))
        elif tip == "p-orta" and onceki in ("p-sol", "p-sayi"):
            akis.append(Spacer(1, 2 * SATIR)); hitap = True
        elif tip in ("p-sol", "p-sayi") and onceki == "p-orta":
            akis.append(Spacer(1, 2 * SATIR))
        elif onceki == "p-orta" and tip != "p-orta" and hitap:
            akis.append(Spacer(1, 2 * SATIR)); hitap = False
        elif onceki == "p-sol" and tip not in ("p-sol", "p-sayi") and ilgi_son:
            akis.append(Spacer(1, SATIR))
        ilgi_son = tip == "p-sol" and bool(re.match(r"^(İlgi|İLGİ)\b", metin if isinstance(metin, str) else "")) or (ilgi_son and tip == "p-sol")
        onceki = tip
        if tip == "hr":
            akis.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey, spaceBefore=6, spaceAfter=6))
        elif tip in ("h2", "h3"):
            akis.append(Paragraph(x(metin), ara))
        elif tip == "h4":
            akis.append(Paragraph(x(metin), alt))
        elif tip == "madde":
            akis.append(Paragraph(f"<b>{pdf_bicim(metin[0])}</b> {pdf_bicim(metin[1])}", govde))
        elif tip == "dipnot":
            akis.append(Paragraph(x(metin), dip))
        elif tip == "p-sayi":
            st = Table([[Paragraph(x(metin[0]), solst), Paragraph(x(metin[1]), sagst)]], colWidths=[12.1 * cm, 4 * cm], hAlign="LEFT")
            st.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
            akis.append(st)
        elif tip.startswith("p-"):
            akis.append(Paragraph(x(metin), {"p-orta": ortast, "p-sag": sagst, "p-imza": imzast, "p-onay": onayst, "p-olur": olurst}.get(tip, solst)))
        else:
            akis.append(Paragraph(pdf_bicim(metin), govde))

    def altbilgi(c, d):
        c.saveState()
        c.setFont(f, 7.5)
        c.setFillColor(colors.grey)
        c.drawString(2 * cm, 1.2 * cm, f"{SITE_ADI} — resmî metin için Resmî Gazete ve ilgili kurum yayını esas alınmalıdır.")
        c.drawRightString(A4[0] - 2 * cm, 1.2 * cm, str(d.page))
        c.restoreState()

    doc = SimpleDocTemplate(str(hedef), pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm, topMargin=2 * cm,
                            bottomMargin=2 * cm, title=b["baslik"], author=SITE_ADI)
    doc.build(akis, onFirstPage=altbilgi, onLaterPages=altbilgi)


# ---------------------------------------------------------------- ana akış
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hizli", action="store_true", help="Word/PDF dosyalarını üretme")
    a = ap.parse_args()
    belgeler = belgeleri_oku()
    if CIKTI.exists():
        shutil.rmtree(CIKTI)
    (CIKTI / "tur").mkdir(parents=True)
    shutil.copytree(KOK / "site" / "assets", CIKTI / "assets")
    (CIKTI / ".nojekyll").write_text("")

    dizin, metin_dizin = [], []
    hatalar = []
    for i, b in enumerate(sorted(belgeler.values(), key=lambda b: sade(b["baslik"]))):
        klasor = CIKTI / "mevzuat" / b["tur"]
        klasor.mkdir(parents=True, exist_ok=True)
        (klasor / f"{b['id']}.html").write_text(belge_sayfasi(b), encoding="utf-8")
        eskiler = list(b.get("eski_kimlikler", []))
        if b.get("eski_tur") and b["eski_tur"] != b["tur"]:  # türü değiştirilen kaydın eski adresi
            eskiler.append((b["eski_tur"], b["id"]))
        for eski_tur, eski_id in eskiler:
            # Birleştirilen kopyaların adresleri çalışmaya devam etsin
            hedef_klasor = CIKTI / "mevzuat" / eski_tur
            hedef_klasor.mkdir(parents=True, exist_ok=True)
            yeni = f"../{b['tur']}/{b['id']}.html"
            (hedef_klasor / f"{eski_id}.html").write_text(
                f'<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url={yeni}">'
                f'<link rel="canonical" href="{yeni}"><a href="{yeni}">{e(b["baslik"])}</a>', encoding="utf-8")
        if b["tam_metin"] and not a.hizli:
            for ad, uretici in (("docx", word_uret), ("pdf", pdf_uret)):
                try:
                    uretici(b, klasor / f"{b['id']}.{ad}")
                except Exception as hata:  # tek belge yüzünden yayın durmasın
                    hatalar.append(f"{b['id']}.{ad}: {hata}")
        dizin.append({"i": b["id"], "b": b["baslik"], "t": b["tur"], "d": b.get("tarih", ""), "s": b.get("sayi", ""),
                      "r": b.get("rg_tarih", ""), "rs": b.get("rg_sayi", ""), "k": b.get("konu", ""),
                      "e": b.get("etiketler", []), "m": 1 if b["tam_metin"] else 0})
        if b["tam_metin"]:
            duz = re.sub(r"[*#<>/]|small", " ", re.sub(r"</?i>", "", b["govde"]))
            duz = re.sub(r"([.…_\-=])\1{3,}", r"\1\1\1", duz)  # nokta/çizgi dizilerini kısalt
            metin_dizin.append({"i": b["id"], "x": re.sub(r"\s+", " ", duz)})
        if (i + 1) % 50 == 0:
            print(f"  {i + 1} belge işlendi", flush=True)

    (CIKTI / "assets" / "dizin.json").write_text(json.dumps(dizin, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    # Tam metin araması için metinler ~2 MB'lık parçalara bölünür; tarayıcı parçaları sırayla indirip tarar
    parca_klasor = CIKTI / "assets" / "metin"
    parca_klasor.mkdir(parents=True, exist_ok=True)
    parcalar, simdiki, boyut = [], [], 0
    for m in metin_dizin:
        simdiki.append(m)
        boyut += len(m["x"].encode("utf-8"))
        if boyut > 2_000_000:
            parcalar.append(simdiki)
            simdiki, boyut = [], 0
    if simdiki:
        parcalar.append(simdiki)
    for n, p in enumerate(parcalar):
        (parca_klasor / f"{n}.json").write_text(json.dumps(p, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (parca_klasor / "parca.json").write_text(json.dumps({"n": len(parcalar), "s": SITE_SURUM}), encoding="utf-8")
    (CIKTI / "index.html").write_text(ana_sayfa(belgeler), encoding="utf-8")
    (CIKTI / "ara.html").write_text(ara_sayfasi(), encoding="utf-8")
    (CIKTI / "hakkinda.html").write_text(hakkinda_sayfasi(belgeler), encoding="utf-8")
    for t in TUR_ADLARI:
        if t in GRUP:  # eski liste adresi birleşik listeye yönlensin
            hedef = f"{GRUP[t]}.html"
            (CIKTI / "tur" / f"{t}.html").write_text(
                f'<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url={hedef}"><a href="{hedef}">{e(TUR_ADLARI[GRUP[t]])}</a>', encoding="utf-8")
        elif any(grup(b["tur"]) == t for b in belgeler.values()):
            (CIKTI / "tur" / f"{t}.html").write_text(tur_sayfasi(t, belgeler), encoding="utf-8")
    print(f"{len(belgeler)} kayıt ({len(metin_dizin)} tam metin) -> {CIKTI}")
    for h in hatalar:
        print("UYARI: indirme dosyası üretilemedi:", h)
    if len(hatalar) > max(5, len(metin_dizin) // 20):
        sys.exit("Çok sayıda Word/PDF dosyası üretilemedi.")


if __name__ == "__main__":
    main()

