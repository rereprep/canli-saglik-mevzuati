#!/usr/bin/env python3
"""Resmî Gazete'yi tarar, sağlıkla ilgili yeni düzenlemeleri siteye ekler.

Her gün GitHub Actions ile çalışır (bkz. .github/workflows/resmi-gazete.yml).
GEMINI_API_KEY ortam değişkeni tanımlıysa Gemini 3.8 Flash ajanı her kaydın
sağlıkla ilgili olup olmadığına karar verir ve künye bilgilerini (tür, konu,
etiketler, birim) çıkarır. Anahtar yoksa anahtar sözcük süzgeci kullanılır.

Kullanım:
  python araclar/rg_takip.py                 # bugünün sayısı
  python araclar/rg_takip.py --tarih 2026-11-04
  python araclar/rg_takip.py --gun 7         # son 7 gün
"""
import argparse, datetime as dt, html, json, os, re, sys, time, unicodedata, urllib.request
from html.parser import HTMLParser
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
TAKIP = KOK / "kaynak-isleme" / "katalog" / "resmi-gazete-takip.json"
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
UA = {"User-Agent": "Mozilla/5.0 (CanliSaglikMevzuati; +https://github.com)"}

ANAHTAR = re.compile(
    r"sağlık|saglik|tıbb|tıp|hekim|hasta|hastane|ilaç|eczac|eczane|kozmetik|aşı|bulaşıcı|hemşire|ebe|"
    r"diş|biyosidal|tütün|organ|doku|kan ürün|laboratuvar|ambulans|acil sağlık|halk sağlığı|hıfzıssıhha|"
    r"gıda|beslenme|engelli|radyasyon|uyuşturucu|bağımlılık|genel sağlık sigortası|tıbbi cihaz|klinik", re.I)

BOLUM_TUR = [
    ("KANUN", "kanun"), ("CUMHURBAŞKANLIĞI KARARNAMES", "cbk"), ("YÖNETMELİK", "yonetmelik"),
    ("TEBLİĞ", "teblig"), ("GENELGE", "genelge"), ("TÜZÜK", "tuzuk"),
]


def getir(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
        ham = r.read()
    for kod in ("utf-8", "windows-1254"):
        try:
            return ham.decode(kod)
        except UnicodeDecodeError:
            pass
    return ham.decode("utf-8", "replace")


class FihristAyristirici(HTMLParser):
    """Günlük fihristteki bölüm başlıklarını ve bağlantıları sırayla toplar."""

    def __init__(self):
        super().__init__()
        self.ogeler, self._href, self._metin, self.bolum = [], None, [], ""
        self._serbest = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._metin = []

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            metin = " ".join("".join(self._metin).split())
            if metin and re.search(r"\.(htm|html|pdf)$", self._href or "", re.I):
                self.ogeler.append({"bolum": self.bolum, "metin": metin, "href": self._href})
            self._href = None

    def handle_data(self, data):
        if self._href is not None:
            self._metin.append(data)
            return
        t = " ".join(data.split())
        if t and t.upper() == t and len(t) > 4 and any(k in t for k, _ in BOLUM_TUR + [("YARGI", ""), ("İLAN", "")]):
            self.bolum = t


def tur_bul(bolum, metin):
    for anahtar, tur in BOLUM_TUR:
        if anahtar in bolum.upper():
            return tur
    m = metin.lower()
    if "yönetmeli" in m:
        return "yonetmelik"
    if "tebliğ" in m:
        return "teblig"
    if "kanun" in m:
        return "kanun"
    return ""


def sade_id(s):
    s = unicodedata.normalize("NFKD", s.lower().replace("ı", "i"))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:90]


def html_metin(sayfa):
    sayfa = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", sayfa)
    sayfa = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>|</h\d>", "\n", sayfa)
    sayfa = html.unescape(re.sub(r"<[^>]+>", " ", sayfa))
    satirlar = [" ".join(s.split()) for s in sayfa.splitlines()]
    return "\n\n".join(s for s in satirlar if s)


def gemini(istem):
    anahtar = os.environ.get("GEMINI_API_KEY")
    if not anahtar:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={anahtar}"
    govde = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": istem}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1},
    }).encode()
    for deneme in range(3):
        try:
            istek = urllib.request.Request(url, data=govde, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(istek, timeout=90) as r:
                yanit = json.loads(r.read())
            return json.loads(yanit["candidates"][0]["content"]["parts"][0]["text"])
        except Exception as hata:  # ağ/kota hatalarında yeniden dene
            print(f"  Gemini hatası ({deneme + 1}/3): {hata}", file=sys.stderr)
            time.sleep(5 * (deneme + 1))
    return None


AJAN_ISTEMI = """Sen bir sağlık hukuku uzmanı ajansın. Aşağıda Resmî Gazete'nin {tarih} tarihli sayısında yayımlanan bir düzenlemenin başlığı ve metninin başı var.
Görevin: Bu düzenlemenin sağlık mevzuatı sitesine eklenip eklenmeyeceğine karar vermek ve künyesini çıkarmak.
Sağlık hizmetleri, sağlık personeli, ilaç/tıbbi cihaz/kozmetik, halk sağlığı, sağlık sigortası, gıda güvenliği ve hasta hakları ile doğrudan ilgili olanlar eklenir; yalnızca bir üniversitenin genel lisansüstü yönetmeliği gibi dolaylı olanlar eklenmez (sağlık bilimleri/tıp fakültesine özgü olanlar eklenir).
Yalnızca şu JSON'u döndür:
{{"ilgili": true/false, "tur": "kanun|cbk|yonetmelik|teblig|genelge|tuzuk", "baslik": "resmi ad", "birim": "yayımlayan kurum", "konu": "tek cümle", "etiketler": ["2-5 küçük harfli etiket"], "degistirilen": "değişiklik düzenlemesiyse değiştirdiği ana düzenlemenin adı, değilse boş"}}

BÖLÜM: {bolum}
BAŞLIK: {baslik}
METİN (ilk kısım):
{metin}
"""


def gun_tara(gun, mevcut):
    yil, ay, g = gun.strftime("%Y"), gun.strftime("%m"), gun.strftime("%Y%m%d")
    fihrist = f"https://www.resmigazete.gov.tr/eskiler/{yil}/{ay}/{g}.htm"
    try:
        sayfa = getir(fihrist)
    except Exception as hata:
        print(f"{gun}: fihrist alınamadı ({hata})")
        return []
    sayi = re.search(r"Sayı\s*:\s*(\d{5})", html.unescape(re.sub(r"<[^>]+>", " ", sayfa)))
    p = FihristAyristirici()
    p.feed(sayfa)
    yeni = []
    for oge in p.ogeler:
        if "İLAN" in oge["bolum"].upper() or "YARGI" in oge["bolum"].upper():
            continue
        url = urllib.request.urljoin(fihrist, oge["href"])
        if url in mevcut:
            continue
        tur = tur_bul(oge["bolum"], oge["metin"])
        if not tur:
            continue
        metin = ""
        if url.lower().endswith((".htm", ".html")):
            try:
                metin = html_metin(getir(url))
            except Exception:
                metin = ""
        karar = gemini(AJAN_ISTEMI.format(tarih=gun.isoformat(), bolum=oge["bolum"], baslik=oge["metin"], metin=metin[:6000]))
        if karar is None:  # Gemini yoksa anahtar sözcük süzgeci
            if not ANAHTAR.search(oge["metin"] + " " + metin[:1500]):
                continue
            karar = {"ilgili": True, "tur": tur, "baslik": re.sub(r"^[–\-–\s]+", "", oge["metin"]), "birim": "", "konu": "", "etiketler": []}
        if not karar.get("ilgili"):
            continue
        kayit = {
            "id": "rg-" + g + "-" + sade_id(karar.get("baslik") or oge["metin"]),
            "baslik": karar.get("baslik") or oge["metin"],
            "tur": karar.get("tur") if karar.get("tur") in {"kanun", "cbk", "yonetmelik", "teblig", "genelge", "tuzuk"} else tur,
            "rg_tarih": gun.isoformat(),
            "rg_sayi": sayi.group(1) if sayi else "",
            "birim": karar.get("birim", ""),
            "konu": karar.get("konu", ""),
            "etiketler": karar.get("etiketler", []),
            "kaynak_url": url,
            "kaynak": f"Resmî Gazete, {gun.strftime('%d.%m.%Y')}" + (f", Sayı {sayi.group(1)}" if sayi else ""),
            "durum": "yürürlükte",
        }
        if karar.get("degistirilen"):
            kayit["not"] = "Değiştirdiği düzenleme: " + karar["degistirilen"]
        if metin:
            kayit["metin"] = metin
        yeni.append(kayit)
        print(f"  + {kayit['baslik']}")
    return yeni


def icerige_yaz(kayit):
    """Tam metni alınabilen kaydı icerik/ altına Markdown olarak yazar."""
    metin = kayit.pop("metin", "")
    if len(metin) < 400:
        return False
    satirlar = ["---"]
    for alan in ["id", "baslik", "tur", "rg_tarih", "rg_sayi", "birim", "konu", "etiketler", "kaynak", "kaynak_url", "not", "durum"]:
        if kayit.get(alan):
            satirlar.append(f"{alan}: {json.dumps(kayit[alan], ensure_ascii=False)}")
    satirlar.append("---")
    govde = []
    for p in metin.split("\n\n"):
        m = re.match(r"^((?:GEÇİCİ |EK )?MADDE\s*\d+[/A-Za-z]*)\s*[-–—]\s*", p)
        if m:
            govde.append(f"**{m.group(1)} –** {p[m.end():]}")
        elif p.isupper() and len(p) < 140:
            govde.append("### " + p)
        else:
            govde.append(p)
    hedef = KOK / "icerik" / kayit["tur"] / f"{kayit['id']}.md"
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_text("\n".join(satirlar) + "\n\n" + "\n\n".join(govde) + "\n", encoding="utf-8")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tarih")
    ap.add_argument("--gun", type=int, default=1)
    a = ap.parse_args()
    bitis = dt.date.fromisoformat(a.tarih) if a.tarih else dt.date.today()
    katalog = json.loads(TAKIP.read_text(encoding="utf-8")) if TAKIP.exists() else []
    mevcut = {k.get("kaynak_url") for k in katalog}
    for md in (KOK / "icerik").glob("*/rg-*.md"):
        m = re.search(r'^kaynak_url: "(.*)"$', md.read_text(encoding="utf-8"), re.M)
        if m:
            mevcut.add(m.group(1))
    eklenen = 0
    for i in range(a.gun - 1, -1, -1):
        gun = bitis - dt.timedelta(days=i)
        print(f"Resmî Gazete {gun.isoformat()} taranıyor…")
        for kayit in gun_tara(gun, mevcut):
            if not icerige_yaz(kayit):
                katalog.append(kayit)
            eklenen += 1
    TAKIP.parent.mkdir(parents=True, exist_ok=True)
    TAKIP.write_text(json.dumps(katalog, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{eklenen} yeni kayıt eklendi.")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"eklenen={eklenen}\n")


if __name__ == "__main__":
    main()

