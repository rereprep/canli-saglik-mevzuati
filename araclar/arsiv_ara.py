#!/usr/bin/env python3
"""Kaldırılmış saglik.gov.tr / mevzuat.gov.tr sayfalarının İnternet Arşivi (Wayback Machine)
kopyalarını arar. Kayıt başına bulunan arşiv adreslerini ../arastirma/sonuc-arsiv.json'a yazar
(kaynaktan_aktar.py bu dosyayı da okur).
Kullanım: python araclar/arsiv_ara.py <kayıt listesi json>"""
import json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path
KOK = Path(__file__).resolve().parent.parent
UA = {'User-Agent': 'Mozilla/5.0 (CanliSaglikMevzuati arşiv araması)'}


def getir(url, deneme=3):
    for i in range(deneme):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except Exception:
            if i == deneme - 1:
                raise
            time.sleep(4 * (i + 1))


def cdx(desen):
    u = 'https://web.archive.org/cdx/search/cdx?' + urllib.parse.urlencode(
        {'url': desen, 'output': 'json', 'filter': 'statuscode:200', 'collapse': 'urlkey', 'limit': '50'})
    try:
        satirlar = json.loads(getir(u) or b'[]')
    except Exception as e:
        print('  cdx hata', desen, e, flush=True)
        return []
    return [dict(zip(satirlar[0], s)) for s in satirlar[1:]] if satirlar else []


def adaylar(k):
    u = k.get('kaynak_url') or ''
    m = re.search(r'saglik\.gov\.tr/TR[-,%2C]+(\d+)', u, re.I)
    if m:
        n = m.group(1)
        return [f'saglik.gov.tr/TR/belge/1-{n}/*', f'saglik.gov.tr/TR,{n}/*', f'saglik.gov.tr/TR-{n}/*', f'www.saglik.gov.tr/TR,{n}/*']
    m = re.search(r'MevzuatKod=(\d+)\.(\d+)\.(\d+)', u) or re.search(r'MevzuatNo=(\d+)&MevzuatTur=(\d+)&MevzuatTertip=(\d+)', u)
    if m:
        if 'MevzuatKod' in m.group(0):
            tur, ter, no = m.groups()
        else:
            no, tur, ter = m.groups()
        return [f'mevzuat.gov.tr/Metin.Aspx?MevzuatKod={tur}.{ter}.{no}*', f'mevzuat.gov.tr/MevzuatMetin/{tur}.{ter}.{no}*',
                f'mevzuat.basbakanlik.gov.tr/Metin.Aspx?MevzuatKod={tur}.{ter}.{no}*']
    return []


def main():
    kayitlar = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    cikti = KOK.parent / 'arastirma' / 'sonuc-arsiv.json'
    sonuc = json.loads(cikti.read_text(encoding='utf-8')) if cikti.exists() else []
    bitti = {s['id'] for s in sonuc}
    for k in kayitlar:
        if k['id'] in bitti:
            continue
        bulunan = []
        for d in adaylar(k):
            bulunan += cdx(d)
            time.sleep(1.5)
        bulunan.sort(key=lambda s: s['timestamp'], reverse=True)
        adresler = []
        for s in bulunan:
            if re.search(r'\.(css|js|jpg|png|gif)$', s['original'], re.I):
                continue
            adresler.append(f"https://web.archive.org/web/{s['timestamp']}/{s['original']}")
        print(len(adresler), k['baslik'][:60], adresler[:1], flush=True)
        sonuc.append({'id': k['id'], 'url': adresler[0] if adresler else '', 'yedek_url': adresler[1] if len(adresler) > 1 else '',
                      'kaynak_turu': 'arşiv', 'not': f'{len(adresler)} arşiv kopyası'})
        cikti.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
