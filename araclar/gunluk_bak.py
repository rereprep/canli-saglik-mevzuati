#!/usr/bin/env python3
"""Günlük güncelleme taraması ("günlük bak"): Resmî Gazete, HSGM mevzuat sayfası ve saglik.gov.tr mevzuat/birim sayfaları.
Sitede (icerik/, yedek/) bulunmayan aday belgeleri listeler; hiçbir dosyayı değiştirmez.
Kullanım: python3 -I araclar/gunluk_bak.py [--gun 3]   (ağ erişimi gerekir)
      python3 -I araclar/gunluk_bak.py --kaydet   (bu çalıştırmadaki tüm adayları "incelendi" listesine ekler)
Çıktı: ekrana özet + calisma/gunluk/<tarih>.json. Daha önce incelenip eklenmemesine karar verilen ya da sitede başka
adla bulunan kayıtlar kaynak-isleme/gunluk/incelenen.json'da tutulur ve yeniden raporlanmaz."""
import datetime as dt, glob, html, json, re, subprocess, sys, unicodedata
from pathlib import Path
KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "araclar"))
from surum_indir import fihrist, fihrist_url  # noqa: E402

SAGLIK = re.compile(r"sağlık|tıbb|tıp\b|hekim|hasta|ilaç|eczac|eczane|kozmetik|aşı\b|bulaşıcı|hemşire|ebelik|diş|biyosidal|tütün|organ|doku|kan ve kan|laboratuvar|ambulans|hıfzıssıhha|gıda|beslenme|engelli|radyasyon|uyuşturucu|bağımlılık|genel sağlık sigortası|cihaz|klinik|psikolog|fizyoterap|diyetisyen|optisyen|diyaliz|aile danışma|ruh sağlığı|adli tıp|sut\b|geri ödeme|hijyen|su\b|çevre|atık|pestisit|zehir|kimyasal|veteriner", re.I)
UA = "Mozilla/5.0"
INCELENEN = KOK / "kaynak-isleme" / "gunluk" / "incelenen.json"


def sade(x):
    x = x.lower().replace("ı", "i").replace("İ", "i")
    x = unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", x).split())


def getir(u):
    return subprocess.run(["curl", "-sL", "--max-time", "60", "-A", UA, u], capture_output=True).stdout.decode("utf-8", "ignore")


def site_bilgisi():
    metin, basliklar = [], set()
    for f in glob.glob(str(KOK / "icerik/*/*.md")) + glob.glob(str(KOK / "yedek/**/*.md"), recursive=True):
        s = open(f, encoding="utf-8", errors="ignore").read()
        metin.append(s[:4000])
        m = re.search(r'^baslik: "([^"]+)"', s, re.M)
        if m:
            basliklar.add(sade(m.group(1)))
    t = "\n".join(metin)
    return t, basliklar, set(re.findall(r"TR-(\d+)", t)) | set(re.findall(r"Eklenti/(\d+)", t))


def sitede_mi(ad, url, metin, basliklar):
    s = sade(re.sub(r"\((?:Karar Sayısı|No)[^)]*\)", "", ad))
    return (url and url in metin) or s in basliklar or any(s and (s in b or b in s) and min(len(s), len(b)) > 25 for b in basliklar)


def resmi_gazete(gun, metin, basliklar):
    out = []
    for i in range(gun):
        t = (dt.date.today() - dt.timedelta(days=i)).isoformat()
        y, a, g = t.split("-")
        try:
            liste = fihrist(t)
        except Exception:
            liste = []
        for n in (1, 2, 3):
            try:
                liste += fihrist_url(f"https://www.resmigazete.gov.tr/eskiler/{y}/{a}/{y}{a}{g}M{n}.htm")
            except Exception:
                break
        for u, m in liste:
            m = m.strip("—–- ")
            if re.match(r"^(a|b|c) -|T\.C\. Merkez|Yargı İlân|Artırma|Çeşitli İlân", m) or "Üniversitesi" in m and not SAGLIK.search(m.split("Üniversitesi")[-1]):
                continue
            if SAGLIK.search(m):
                out.append({"kaynak": "Resmî Gazete", "tarih": t, "ad": m, "url": u, "sitede": sitede_mi(m, u, metin, basliklar)})
    return out


def hsgm(metin, basliklar):
    s = getir("https://hsgm.saglik.gov.tr/tr/mevzuat.html")
    m = re.search(r"publications\s*[:=]\s*(\[.*?\])\s*[,;]\s*\n", s, re.S)
    if not m:
        return [{"kaynak": "HSGM", "ad": "LİSTE OKUNAMADI", "url": "", "sitede": False}]
    out = []
    for x in json.loads(m.group(1)):
        if not sitede_mi(x["title"], x["url"], metin, basliklar):
            out.append({"kaynak": "HSGM", "tarih": x["created"][:10], "ad": x["title"], "url": x["url"], "kategori": x["category"], "sitede": False})
    return out


def saglik_gov(metin, basliklar, numaralar):
    agac = getir("https://www.saglik.gov.tr/TR-11186/yonergeler.html")
    oge = re.findall(r'<a id="(\d+)" href="(/TR-(\d+)/[^"]+)"[^>]*>\s*(.*?)\s*</a>', agac, re.S)
    birim = re.compile(r"(Genel Müdürlüğü|Başkanlığı|Kurumu|Birimi)\s*$")
    sayfalar = [h for _, h, _, t in oge if birim.search(html.unescape(t).strip())]
    sayfalar += ["/TR-10357/saglik-mevzuati.html", "/TR-10358/kanunlar.html", "/TR-10413/yonetmelikler.html",
                 "/TR-10535/genelgeler.html", "/TR-11186/yonergeler.html", "/TR-11293/tuzukler.html", "/TR-11300/tebligler.html"]
    gor, out = set(), []
    for h in sayfalar:
        p = getir("https://www.saglik.gov.tr" + h)
        for u, t in re.findall(r'href="([^"]*/TR-\d+/[^"]*)"[^>]*>(.*?)</a>', p, re.S):
            n = re.search(r"TR-(\d+)", u).group(1)
            t = " ".join(html.unescape(re.sub("<[^>]+>", "", t)).split())
            if n in gor or n in numaralar or len(t) < 15:
                continue
            gor.add(n)
            if re.search(r"yönerge|genelge|yönetmeli|tebliğ|usul ve esas|kanun|karar|talimat", t, re.I) and not sitede_mi(t, "", metin, basliklar):
                out.append({"kaynak": "saglik.gov.tr", "ad": t, "url": "https://www.saglik.gov.tr" + u if u.startswith("/") else u, "sitede": False})
    return out


def main():
    gun = int(sys.argv[sys.argv.index("--gun") + 1]) if "--gun" in sys.argv else 3
    metin, basliklar, numaralar = site_bilgisi()
    sonuc = {"rg": resmi_gazete(gun, metin, basliklar), "hsgm": hsgm(metin, basliklar), "saglik_gov": saglik_gov(metin, basliklar, numaralar)}
    incelenen = set(json.loads(INCELENEN.read_text(encoding="utf-8"))) if INCELENEN.exists() else set()
    anahtar = lambda x: x.get("url") or sade(x["ad"])
    if "--kaydet" in sys.argv:
        incelenen |= {anahtar(x) for v in sonuc.values() for x in v}
        INCELENEN.write_text(json.dumps(sorted(incelenen), ensure_ascii=False, indent=0), encoding="utf-8")
    for k in sonuc:
        sonuc[k] = [x for x in sonuc[k] if anahtar(x) not in incelenen or x.get("kaynak") == "Resmî Gazete"]
    yol = KOK / "calisma" / "gunluk"
    yol.mkdir(parents=True, exist_ok=True)
    (yol / f"{dt.date.today().isoformat()}.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in sonuc.items():
        print(f"== {k}: {len(v)} aday")
        for x in v:
            print(("  [sitede] " if x.get("sitede") else "  [YENİ?]  ") + f"{x.get('tarih','')} {x['ad'][:140]} | {x['url']}")


if __name__ == "__main__":
    main()
