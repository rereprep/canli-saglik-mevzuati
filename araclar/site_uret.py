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
SITE_ADI = "Canlı Sağlık Mevzuatı"

TUR_ADLARI = {
    "kanun": "Kanunlar",
    "cbk": "Cumhurbaşkanlığı Kararnameleri",
    "khk": "Kanun Hükmünde Kararnameler",
    "tuzuk": "Tüzükler",
    "yonetmelik": "Yönetmelikler",
    "yonerge": "Yönergeler",
    "genelge": "Genelgeler",
    "teblig": "Tebliğler",
    "protokol": "Protokoller",
    "yazi": "Resmî Yazılar ve Talimatlar",
}
TUR_TEKIL = {
    "kanun": "Kanun", "cbk": "Cumhurbaşkanlığı Kararnamesi", "khk": "Kanun Hükmünde Kararname",
    "tuzuk": "Tüzük", "yonetmelik": "Yönetmelik", "yonerge": "Yönerge", "genelge": "Genelge",
    "teblig": "Tebliğ", "protokol": "Protokol", "yazi": "Resmî Yazı",
}


# ---------------------------------------------------------------- veri okuma
def on_bilgi_ayir(metin):
    metin = unicodedata.normalize("NFC", metin)
    if not metin.startswith("---\n"):
        return {}, metin
    son = metin.index("\n---\n", 4)
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
    for js in sorted((KOK / "kaynak-isleme" / "zenginlestirme").glob("*.json")):
        ek.update(json.loads(js.read_text(encoding="utf-8")))
    for md in sorted((KOK / "icerik").glob("*/*.md")):
        veri, govde = on_bilgi_ayir(md.read_text(encoding="utf-8"))
        for alan, deger in ek.get(veri["id"], {}).items():
            if deger and (not veri.get(alan) or alan in ("baslik", "konu", "etiketler")):
                veri[alan] = deger
        veri["govde"] = govde
        veri["tam_metin"] = True
        tam.append(veri)
    belgeler = tekillestir(tam)
    for js in sorted((KOK / "kaynak-isleme" / "katalog").glob("*.json")):
        for k in json.loads(js.read_text(encoding="utf-8")):
            if k.get("tur") not in TUR_ADLARI or not k.get("baslik"):
                continue
            k["baslik"] = unicodedata.normalize("NFC", " ".join(k["baslik"].split()))
            k["etiketler"] = [t.replace("-", " ") for t in k.get("etiketler", []) if t]
            if not k.get("id"):
                k["id"] = "k-" + sade(k["baslik"]).replace(" ", "-")[:90]
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
            k["tam_metin"] = False
            k.setdefault("durum", "yürürlükte")
            belgeler.setdefault(k["id"], k)
            _ES_DIZIN = None
    return belgeler


def baslik_anahtari(b):
    s = re.sub(r"^\s*(\d+\.)+\d*\s*", "", b.get("baslik", ""))
    if b.get("tur") == "genelge" and re.fullmatch(r"\d{4}/\d+", b.get("sayi", "")):
        return ("genelge", "no:" + b["sayi"])
    s = re.sub(r"\(\s*\d{4}\s*/\s*\d+\s*\)", "", s)
    return (b.get("tur"), sade(s))


def oncelik(b):
    """Aynı belgenin birden çok kopyası varsa en temiz metni seç."""
    puan = 0
    if b["id"].startswith("dx-"):
        puan += 40
    if not b.get("ocr") or b.get("duzeltildi"):
        puan += 20
    if b["id"].startswith("sbg-"):
        puan += 5
    return puan + min(len(b.get("govde", "")) / 100000, 1)


def tekillestir(liste):
    gruplar = {}
    for b in liste:
        gruplar.setdefault(baslik_anahtari(b), []).append(b)
    sonuc = {}
    for grup in gruplar.values():
        grup.sort(key=oncelik, reverse=True)
        ana = grup[0]
        for diger in grup[1:]:
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
    return s


def md_html(govde):
    parcalar, sayac = [], 0
    for blok in re.split(r"\n{2,}", govde.strip()):
        blok = blok.strip()
        if not blok:
            continue
        if blok == "---":
            parcalar.append("<hr>")
            continue
        satirlar = [s.strip() for s in blok.split("\n")]
        if len(satirlar) >= 1 and all(s.startswith("|") for s in satirlar):
            govde_satir = [s for s in satirlar if not re.fullmatch(r"\|[\s:|-]+\|?", s)]
            hucreler = [[satir_ici(h.strip()) for h in s.strip("|").split("|")] for s in govde_satir]
            parcalar.append('<div class="tablo-kap"><table class="metin-tablo">' + "".join(
                "<tr>" + "".join(f"<td>{h}</td>" for h in r) + "</tr>" for r in hucreler) + "</table></div>")
            continue
        m = re.match(r"^(#{2,4}) (.*)$", blok, re.S)
        if m:
            seviye = len(m.group(1))
            parcalar.append(f"<h{seviye}>{satir_ici(m.group(2))}</h{seviye}>")
            continue
        if blok.startswith("**") and re.match(r"^\*\*(?:GEÇİCİ |Geçici |EK |Ek )?(?:MADDE|Madde)", blok):
            sayac += 1
            no = re.search(r"\d+[/A-Za-z]*", blok)
            kimlik = "madde-" + (no.group(0).lower().replace("/", "-") if no else str(sayac))
            if "geçici" in blok[:15].lower():
                kimlik = "gecici-" + kimlik
            parcalar.append(f'<p class="madde" id="{kimlik}">{satir_ici(blok)}</p>')
            continue
        parcalar.append("<p>" + "<br>".join(satir_ici(s) for s in blok.split("\n")) + "</p>")
    return "\n".join(parcalar)


def duz_bloklar(govde):
    """Word/PDF üretimi için (tip, metin) listesi."""
    govde = XML_DISI.sub("", govde)
    for blok in re.split(r"\n{2,}", govde.strip()):
        blok = blok.strip()
        if not blok:
            continue
        if blok == "---":
            yield ("hr", "")
        elif blok.startswith("**Dipnotlar**"):
            yield ("h4", "Dipnotlar")
        elif re.match(r"^#{2,4} ", blok):
            yield ("h" + str(len(blok.split(" ")[0])), blok.split(" ", 1)[1])
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
<link rel="stylesheet" href="{kok}assets/stil.css">
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
    <p class="ithaf"><em>Her zaman ufkumu açan Prof. Dr. Cemil Özcan'a en derin saygılarımla.</em></p>
    <p class="uyari">Bu site resmî bir kaynak değildir. Metinler derlenmiş kitaplardan ve resmî sitelerden aktarılmıştır; hukuki işlemlerde Resmî Gazete ve ilgili kurumun yayımladığı metin esas alınmalıdır.</p>
  </div>
</footer>
<script src="{kok}assets/ara.js" defer></script>
</body>
</html>
"""


def belge_sayfasi(b):
    kok = "../../"
    k = "".join(f"<tr><th>{e(a)}</th><td>{e(v)}</td></tr>" for a, v in kunye(b))
    if b.get("kaynak_url"):
        k += f'<tr><th>Resmî Kaynak</th><td><a href="{e(b["kaynak_url"])}" rel="noopener" target="_blank">{e(b["kaynak_url"])}</a></td></tr>'
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
    icerik = f"""<nav class="yol"><a href="{kok}index.html">Ana Sayfa</a> › <a href="{kok}tur/{b['tur']}.html">{e(TUR_ADLARI[b['tur']])}</a></nav>
<h1 class="belge-baslik">{e(b['baslik'])}</h1>
{indir}
<table class="kunye">{k}</table>
<div class="etiketler">{etiket}</div>
{ara}
{govde}"""
    return sayfa(b["baslik"], icerik, kok, b.get("konu", ""))


def sirala_anahtar(b):
    return (b.get("rg_tarih") or b.get("tarih") or "0000")


def tablo(belgeler, kok):
    satirlar = []
    for b in belgeler:
        rg = " / ".join(x for x in [tarih_tr(b.get("rg_tarih")), b.get("rg_sayi")] if x)
        isaret = "" if b["tam_metin"] else ' <span class="rozet">künye</span>'
        satirlar.append(
            f'<tr><td><a href="{kok}mevzuat/{b["tur"]}/{e(b["id"])}.html">{e(b["baslik"])}</a>{isaret}</td>'
            f'<td>{e(TUR_TEKIL[b["tur"]])}</td><td>{e(tarih_tr(b.get("tarih")))}</td><td>{e(b.get("sayi"))}</td><td>{e(rg)}</td></tr>')
    return ('<table class="liste"><thead><tr><th>Mevzuat Adı</th><th>Tür</th><th>Tarih</th><th>Sayı</th><th>Resmî Gazete</th></tr></thead><tbody>'
            + "".join(satirlar) + "</tbody></table>")


def ana_sayfa(belgeler):
    sayac = {t: 0 for t in TUR_ADLARI}
    for b in belgeler.values():
        sayac[b["tur"]] += 1
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
    liste = sorted((b for b in belgeler.values() if b["tur"] == tur), key=lambda b: sade(b["baslik"]))
    icerik = f"""<nav class="yol"><a href="../index.html">Ana Sayfa</a> › {e(TUR_ADLARI[tur])}</nav>
<h1>{e(TUR_ADLARI[tur])} <small>({len(liste)})</small></h1>
<div class="metin-ara"><input type="search" id="liste-suz" placeholder="Bu listede süz…" aria-label="Listede süz"></div>
{tablo(liste, "../")}"""
    return sayfa(TUR_ADLARI[tur], icerik, "../")


def ara_sayfasi():
    turler = "".join(f'<label><input type="checkbox" name="tur" value="{t}" checked> {e(ad)}</label>' for t, ad in TUR_ADLARI.items())
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
    from docx.enum.text import WD_ALIGN_PARAGRAPH
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
            p.add_run(metin[0] + " ").bold = True
            p.add_run(metin[1])
        elif tip == "dipnot":
            p = d.add_paragraph()
            r = p.add_run(metin)
            r.font.size = Pt(8)
            r.font.color.rgb = RGBColor(0x44, 0x44, 0x44)
        else:
            p = d.add_paragraph(metin)
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
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
    adaylar = [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"),
        ("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf", "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"),
        ("/System/Library/Fonts/Supplemental/Times New Roman.ttf", "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf"),
        ("/Library/Fonts/Arial Unicode.ttf", "/Library/Fonts/Arial Unicode.ttf"),
    ]
    for normal, kalin in adaylar:
        if Path(normal).exists() and Path(kalin).exists():
            pdfmetrics.registerFont(TTFont("Govde", normal))
            pdfmetrics.registerFont(TTFont("Govde-Kalin", kalin))
            from reportlab.lib.fonts import addMapping
            addMapping("Govde", 0, 0, "Govde")
            addMapping("Govde", 1, 0, "Govde-Kalin")
            addMapping("Govde", 0, 1, "Govde")
            addMapping("Govde", 1, 1, "Govde-Kalin")
            _FONT = "Govde"
            return _FONT
    raise SystemExit("Türkçe karakter destekli bir TTF yazı tipi bulunamadı (DejaVu veya Liberation kurun).")


def pdf_uret(b, hedef):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, HRFlowable

    f = font_kaydet()
    govde = ParagraphStyle("g", fontName=f, fontSize=10.5, leading=14, alignment=TA_JUSTIFY, spaceAfter=5)
    baslik = ParagraphStyle("b", parent=govde, fontName=f + "-Kalin", fontSize=13, leading=17, alignment=TA_CENTER, spaceAfter=10)
    ara = ParagraphStyle("a", parent=govde, fontName=f + "-Kalin", alignment=TA_CENTER, spaceBefore=6)
    alt = ParagraphStyle("h4", parent=govde, fontName=f + "-Kalin", spaceAfter=1, spaceBefore=4)
    dip = ParagraphStyle("d", parent=govde, fontSize=8, leading=10, textColor=colors.HexColor("#444444"))
    kucuk = ParagraphStyle("k", parent=govde, fontSize=8.5, leading=11, alignment=0)

    def x(s):
        return html.escape(s, quote=False)

    akis = [Paragraph(x(b["baslik"].upper()), baslik)]
    t = Table([[Paragraph("<b>" + x(a) + "</b>", kucuk), Paragraph(x(v), kucuk)] for a, v in kunye(b)], colWidths=[4 * cm, 12.5 * cm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
                           ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2f7")),
                           ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    akis += [t, Spacer(1, 10)]
    for tip, metin in duz_bloklar(b["govde"]):
        if tip == "hr":
            akis.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey, spaceBefore=6, spaceAfter=6))
        elif tip in ("h2", "h3"):
            akis.append(Paragraph(x(metin), ara))
        elif tip == "h4":
            akis.append(Paragraph(x(metin), alt))
        elif tip == "madde":
            akis.append(Paragraph(f"<b>{x(metin[0])}</b> {x(metin[1])}", govde))
        elif tip == "dipnot":
            akis.append(Paragraph(x(metin), dip))
        else:
            akis.append(Paragraph(x(metin), govde))

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
        for eski_tur, eski_id in b.get("eski_kimlikler", []):
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
            duz = re.sub(r"[*#<>/]|small", " ", b["govde"])
            metin_dizin.append({"i": b["id"], "x": re.sub(r"\s+", " ", duz)})
        if (i + 1) % 50 == 0:
            print(f"  {i + 1} belge işlendi", flush=True)

    (CIKTI / "assets" / "dizin.json").write_text(json.dumps(dizin, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (CIKTI / "assets" / "metinler.json").write_text(json.dumps(metin_dizin, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (CIKTI / "index.html").write_text(ana_sayfa(belgeler), encoding="utf-8")
    (CIKTI / "ara.html").write_text(ara_sayfasi(), encoding="utf-8")
    (CIKTI / "hakkinda.html").write_text(hakkinda_sayfasi(belgeler), encoding="utf-8")
    for t in TUR_ADLARI:
        if any(b["tur"] == t for b in belgeler.values()):
            (CIKTI / "tur" / f"{t}.html").write_text(tur_sayfasi(t, belgeler), encoding="utf-8")
    print(f"{len(belgeler)} kayıt ({len(metin_dizin)} tam metin) -> {CIKTI}")
    for h in hatalar:
        print("UYARI: indirme dosyası üretilemedi:", h)
    if len(hatalar) > max(5, len(metin_dizin) // 20):
        sys.exit("Çok sayıda Word/PDF dosyası üretilemedi.")


if __name__ == "__main__":
    main()

