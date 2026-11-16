"""Genelge ve resmî yazılar için Sağlık Bakanlığı birim etiketleri.

Birim; belgenin antetinden (ilk satırlardaki "… Genel Müdürlüğü / … Dairesi Başkanlığı") ve künyedeki
`birim` alanından çıkarılır, yazım farkları tek ada indirilir. Daire başkanlığına bağlı olduğu genel
müdürlük, kapatılmış birime de görevi devralan bugünkü birim eklenir.
"""
import difflib
import re

HSGM = "Halk Sağlığı Genel Müdürlüğü"
SHGM = "Sağlık Hizmetleri Genel Müdürlüğü"
KHGM = "Kamu Hastaneleri Genel Müdürlüğü"
YHGM = "Yönetim Hizmetleri Genel Müdürlüğü"
HHGM = "Hukuk Hizmetleri Genel Müdürlüğü"
SBSGM = "Sağlık Bilgi Sistemleri Genel Müdürlüğü"
SYGM = "Sağlık Yatırımları Genel Müdürlüğü"
TITCK = "Türkiye İlaç ve Tıbbi Cihaz Kurumu"

# Genel müdürlük düzeyindeki (ya da doğrudan Bakanlığa bağlı) birimler
UST_BIRIMLER = [
    HSGM, SHGM, KHGM, YHGM, HHGM, SBSGM, SYGM, TITCK,
    "Acil Sağlık Hizmetleri Genel Müdürlüğü", "Sağlığın Geliştirilmesi Genel Müdürlüğü",
    "Strateji Geliştirme Başkanlığı", "Teftiş Kurulu Başkanlığı", "Denetim Hizmetleri Başkanlığı",
    "Destek Hizmetleri Genel Müdürlüğü", "Türkiye Halk Sağlığı Kurumu", "Türkiye Kamu Hastaneleri Kurumu",
    "Temel Sağlık Hizmetleri Genel Müdürlüğü", "Tedavi Hizmetleri Genel Müdürlüğü",
    "Ana Çocuk Sağlığı ve Aile Planlaması Genel Müdürlüğü", "Personel Genel Müdürlüğü",
    "İlaç ve Eczacılık Genel Müdürlüğü", "Sağlık Eğitimi Genel Müdürlüğü",
    "Verem Savaşı Dairesi Başkanlığı", "Kanserle Savaş Dairesi Başkanlığı", "Sıtma Savaşı Dairesi Başkanlığı",
    "İdari ve Mali İşler Dairesi Başkanlığı", "Bilgi İşlem Dairesi Başkanlığı", "İnşaat ve Onarım Dairesi Başkanlığı",
    "Hukuk Müşavirliği", "Müsteşarlık", "Bakan Yardımcılığı", "Sağlık Bakanlığı",
]

# Kapatılan birim -> görevi devralan bugünkü birim(ler)
HALEF = {
    "Türkiye Halk Sağlığı Kurumu": [HSGM],
    "Temel Sağlık Hizmetleri Genel Müdürlüğü": [HSGM],
    "Ana Çocuk Sağlığı ve Aile Planlaması Genel Müdürlüğü": [HSGM],
    "Verem Savaşı Dairesi Başkanlığı": [HSGM],
    "Kanserle Savaş Dairesi Başkanlığı": [HSGM],
    "Sıtma Savaşı Dairesi Başkanlığı": [HSGM],
    "Türkiye Kamu Hastaneleri Kurumu": [KHGM],
    "Tedavi Hizmetleri Genel Müdürlüğü": [SHGM],
    "Personel Genel Müdürlüğü": [YHGM],
    "İdari ve Mali İşler Dairesi Başkanlığı": [YHGM],
    "Hukuk Müşavirliği": [HHGM],
    "Bilgi İşlem Dairesi Başkanlığı": [SBSGM],
    "İnşaat ve Onarım Dairesi Başkanlığı": [SYGM],
    "İlaç ve Eczacılık Genel Müdürlüğü": [TITCK],
}

# Antette görülse de Sağlık Bakanlığı birimi olmayanlar (yalnız künyedeki birim alanından etiket olur)
DIS = ("cumhurbaskanligi", "sosyal guvenlik kurumu", "afet ve acil durum", "is sagligi ve guvenligi genel",
       "butce ve mali kontrol", "basbakanlik", "yuksekogretim", "maliye")

_KUCUK = {"ve", "ile"}
_ANTET = re.compile(
    r"([A-ZÇĞİÖŞÜa-zçğıöşüâîû ,]{3,90}?(?:Genel M[üu]d[üu]rl[üu][ğg][üu]|Daire(?:si)? Ba[şs]kanl[ıi][ğg][ıi]"
    r"|Kurumu(?: Ba[şs]kanl[ıi][ğg][ıi])?|Kurulu Ba[şs]kanl[ıi][ğg][ıi]|Ba[şs]kanl[ıi][ğg][ıi]|M[üu][şs]avirli[ğg]i))", re.I)


def _kucuk(s):
    return s.replace("İ", "i").replace("I", "ı").lower()


def _sade(s):
    return re.sub(r"[^a-z0-9]+", " ", _kucuk(s).translate(str.maketrans("çğıöşüâîû", "cgiosuaiu"))).strip()


def _baslik(s):
    out = []
    for i, w in enumerate(_kucuk(s).split()):
        if w in _KUCUK and i:
            out.append(w)
        else:
            out.append(("İ" if w[0] == "i" else "I" if w[0] == "ı" else w[0].upper()) + w[1:])
    return " ".join(out)


def duzgun_ad(ham):
    """Antetten ya da künyeden gelen ham birim adını tek biçime indirir; birim değilse '' döndürür."""
    s = re.sub(r"[*#_>|\"“”]", " ", ham or "")
    s = re.sub(r"\bT\.? ?C\.?\b", " ", s)
    s = re.sub(r"(?i)\bSA[ĞG]LIK BAKANLI[ĞG]I\b,?", " ", s) if _sade(s) != "saglik bakanligi" else s
    s = re.sub(r"\b(HSGM|TKHK|THSK|SHGM|KHGM)\b", " ", s)
    s = re.sub(r"\s+", " ", s).strip(" ,.-:")
    if not s:
        return ""
    s = _baslik(s)
    s = re.sub(r"Daire Başkanlığı$", "Dairesi Başkanlığı", s)
    s = re.sub(r"(Kurumu) Başkanlığı$", r"\1", s)
    s = s.replace("Mudurlugu", "Müdürlüğü")
    return s


class Birimler:
    def __init__(self, belgeler):
        """belgeler: {id: belge}. Künyelerdeki birim adlarından ve sık geçen antet adlarından sözlük kurar."""
        self.bilinen = {}
        for ad in UST_BIRIMLER:
            self.bilinen[_sade(ad)] = ad
        say = {}
        self._antet = {}
        for b in belgeler.values():
            if b.get("tur") not in ("genelge", "yazi"):
                continue
            for parca in re.sub(r"(Müdürlüğü|Başkanlığı|Kurumu),\s+", r"\1\n", b.get("birim", "") or "").split("\n"):
                ad = duzgun_ad(parca)
                if ad and re.search(r"(Müdürlüğü|Başkanlığı|Kurumu|Müşavirliği)$", ad):
                    self.bilinen.setdefault(_sade(ad), ad)
            adaylar = self._antet_adaylari(b.get("govde", ""))
            self._antet[b["id"]] = adaylar
            for a in adaylar:
                say[_sade(a)] = say.get(_sade(a), 0) + 1
        self._say = say
        # HSGM'ye bağlı daireler: HSGM kaynaklı belgelerin künyesindeki daire adları
        self.ust = {}
        for b in belgeler.values():
            ad = self.eslestir(duzgun_ad(b.get("birim", "")))
            if ad and ad.endswith("Dairesi Başkanlığı") and ad not in UST_BIRIMLER and (
                    b["id"].startswith("hsgm-") or "hsgm.saglik.gov.tr" in (b.get("kaynak_url") or "") + (b.get("kaynak") or "")):
                self.ust[ad] = HSGM

    @staticmethod
    def _antet_adaylari(govde):
        out = []
        for ln in re.sub(r"<[^>]+>", " ", govde[:1100]).split("\n"):
            ln = re.sub(r"[*#_>|]", "", ln).strip()
            if not ln or len(ln) > 110:
                continue
            if re.match(r"(Say[ıi]|Konu|[İI]lgi|GENELGE)\b", ln):
                if out:
                    break
                continue
            for m in _ANTET.finditer(ln):
                ad = duzgun_ad(m.group(1))
                if ad and 2 <= len(ad.split()) <= 10 and not any(d in _sade(ad) for d in DIS):
                    out.append(ad)
        return out

    def eslestir(self, ad):
        """Yazım farklarını bilinen birim adına indirir; tanınmıyorsa '' döndürür."""
        if not ad:
            return ""
        k = _sade(ad)
        if k in self.bilinen:
            return self.bilinen[k]
        yakin = difflib.get_close_matches(k, list(self.bilinen), n=1, cutoff=0.9)
        if yakin:
            return self.bilinen[yakin[0]]
        # bilinmeyen ama düzgün ve en az iki belgede geçen antet adı
        if self._say.get(k, 0) >= 2 and len(k.split()) >= 3 and re.search(r"(Müdürlüğü|Dairesi Başkanlığı|Kurumu|Müşavirliği)$", ad):
            self.bilinen[k] = ad
            return ad
        return ""

    def etiketler(self, b):
        """Belgenin birim etiketleri: önce genel müdürlük düzeyi, sonra daire başkanlıkları."""
        antet = [x for x in (self.eslestir(a) for a in self._antet.get(b["id"], [])) if x and x != "Sağlık Bakanlığı"]
        kunyeler = []
        for parca in re.sub(r"(Müdürlüğü|Başkanlığı|Kurumu),\s+", r"\1\n", b.get("birim", "") or "").split("\n"):
            parca = parca.strip()
            if parca:
                ad = duzgun_ad(parca)
                kunyeler.append(self.eslestir(ad) or (ad if re.search(r"(Müdürlüğü|Başkanlığı|Kurumu)$", ad) else parca))
        kunye = kunyeler[0] if kunyeler else ""
        ham = antet + kunyeler
        ust, daire = [], []
        antet_ust = [x for x in antet if x in UST_BIRIMLER]
        for ad in ham:
            (ust if ad in UST_BIRIMLER or not ad.endswith("Dairesi Başkanlığı") else daire).append(ad)
        for d in daire:
            if d in self.ust:
                ust.append(self.ust[d])
            elif not antet_ust and not ust:
                pass
        for u in list(ust):
            ust.extend(HALEF.get(u, []))
        for d in list(daire):
            ust.extend(HALEF.get(d, []))
        sonuc = []
        for ad in ust + daire:
            if ad and ad not in sonuc and ad != "Sağlık Bakanlığı":
                sonuc.append(ad)
        return sonuc or (["Sağlık Bakanlığı"] if kunye == "Sağlık Bakanlığı" else [])
