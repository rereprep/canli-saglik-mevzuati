"""Kaynak güncellemesinde yakalanan fihrist/sınıflandırma hataları."""
import datetime as dt
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rg_takip as rg
import site_uret as site


class GuncellemeTest(unittest.TestCase):
    def test_fihrist_sayi_bicimleri(self):
        self.assertEqual(rg.rg_sayisi('<p>Sayı : <b>33433</b></p>'), '33433')
        self.assertEqual(rg.rg_sayisi('<title>33433 Sayılı Resmî Gazete</title>'), '33433')
        self.assertEqual(rg.rg_sayisi('Numarasız içerik'), '')

    def test_diyaliz_yeni_kayit_ve_url_farkli_kopya(self):
        fihrist = '<title>33429 Sayılı Resmî Gazete</title><p>YÖNETMELİKLER</p>' \
                  '<a href="20261113-1.htm">Diyaliz Merkezleri Hakkında Yönetmelik</a>'
        gun = dt.date(2026, 11, 13)
        with patch.object(rg, 'getir', side_effect=[fihrist, '<p>MADDE 1 – İçerik</p>']):
            aday = rg.gun_tara(gun, set())
        self.assertEqual(len(aday), 1)
        self.assertEqual(aday[0]['rg_sayi'], '33429')
        with patch.object(rg, 'getir', return_value=fihrist) as getir:
            aday = rg.gun_tara(gun, set(), {(rg.sade_id('Diyaliz Merkezleri Hakkında Yönetmelik'), '2026-11-13')})
        self.assertEqual(aday, [])
        self.assertEqual(getir.call_count, 1)

    def test_ilgisiz_baslik_govdesi_indirilmez(self):
        h = '<p>YÖNETMELİKLER</p><a href="20261117-1.htm">Meteoroloji Mühendisleri Odası Yönetmeliği</a>'
        with patch.object(rg, 'getir', return_value=h) as getir:
            self.assertEqual(rg.gun_tara(dt.date(2026, 11, 17), set()), [])
        self.assertEqual(getir.call_count, 1)

    def test_karar_kararname_ayrimi_ve_son_degisiklik(self):
        b = {'tur': 'bkk', 'tarih': '1978-06-06', 'rg_tarih': '1978-06-28',
             'govde': '**Madde 7 –** (Ek:RG-14/11/2026-33430-CK-11982/12 md.) Metin.'}
        tablo = site._govdeden_liste(b)
        self.assertIn('CK/11982', str(tablo))
        self.assertNotIn('CBK/11982', str(tablo))
        site.son_degisiklik_bul(b)
        self.assertEqual(b['son_degisiklik'], '2026-11-14')
        b['govde'] = '**MADDE 1 –** (Ek:RG-1/1/2026-33124-CBK-200/1 md.) Metin.'
        self.assertIn('CBK/200', str(site._govdeden_liste(b)))

    def test_ana_sayfa_gorunen_tarih_son_degisikliktir(self):
        b = {'id': 'adli', 'baslik': 'Adli Tıp', 'tur': 'yonetmelik', 'tam_metin': True,
             'tarih': '2015-03-28', 'rg_tarih': '2015-03-28', 'son_degisiklik': '2026-11-17'}
        self.assertIn('<td>17.11.2026</td>', site.tablo([b], '', son_tarih=True))
        self.assertIn('<td>28.03.2015</td>', site.tablo([b], ''))

    def test_yonerge_degisiklik_listesi_ve_son_degisiklik(self):
        govde = ('#### (Değişik 19/07/2023- E-20986060-010.04-220260953) İdari İşler Dairesi Başkanlığı\n\n'
                 '**MADDE 27 –** (1) Görevler:\n\n'
                 'a) **(Değişik 18/11/2022 tarihli ve E-43252159-020-2915)** Metin.\n\n'
                 'b) (Degişik: 14.01.2023 tarihli ve E-39434888-612.02-207119253 sayılı Bakan Onayı) OCR\n\n'
                 'c) (Değişik: 16.01.2023 tarihli ve E-39434888-612.02-207119253 sayılı Bakan Onayı) Metin.\n\n'
                 'ç) (Ek: 16.01.2023 tarihli ve E-39434888-612.02-207119253 sayılı Bakan Onayı) Metin.\n\n'
                 '## Ek-2. Şema\n\n(Değişik: 19/11/2025 tarihli ve E-11045126-010.04-295293388 sayılı Bakan Oluru)\n')
        b = {'id': 'y', 'tur': 'yonerge', 'tam_metin': True, 'tarih': '2017-10-02', 'sayi': '1957', 'govde': govde}
        tablo = site._yonerge_listesi(b)
        self.assertEqual(tablo[1], ['02.10.2017', '1957', 'İlk onay'])
        satirlar = {r[0]: r for r in tablo[2:]}
        self.assertEqual(set(satirlar), {'18.11.2022', '16.01.2023', '19.07.2023', '19.11.2025'})  # OCR'lı 14.01 birleşti
        self.assertEqual(satirlar['19.07.2023'][2], '27')  # başlıktaki not izleyen maddeye
        self.assertEqual(satirlar['19.11.2025'][2], 'Ek-2')
        site.degisiklik_listesi_ekle(b)
        site.son_degisiklik_bul(b)
        self.assertIn('## DEĞİŞİKLİK LİSTESİ', b['govde'])
        self.assertEqual(b['son_degisiklik'], '2025-11-19')

    def test_genelge_degisiklik_ve_mulga_son_degisiklik(self):
        hedef = {'id': 'g1', 'tur': 'genelge', 'tam_metin': True, 'tarih': '2008-06-05', 'sayi': '2008/42',
                 'govde': 'Metin (Değişik: RG-12/3/2020-31066) kanun alıntısı.'}
        degistiren = {'id': 'g2', 'tur': 'genelge', 'tarih': '2011-10-19', 'sayi': '2011/56',
                      'degistirdigi': [{'id': 'g1', 'aciklama': 'Bölüm kaldırıldı'}]}
        kaldiran = {'id': 'g3', 'tur': 'genelge', 'tarih': '2024-12-04', 'sayi': '2024/11'}
        mulga = {'id': 'g4', 'tur': 'genelge', 'tarih': '2016-01-01', 'kaldiran': 'g3', 'durum': 'yürürlükten kaldırıldı'}
        notlu = {'id': 't1', 'tur': 'tuzuk', 'rg_tarih': '1985-09-07', 'durum': 'yürürlükten kaldırıldı',
                 'konu': '28/10/2023 tarihli ve 32353 sayılı Resmî Gazete’de yayımlanan Karar ile yürürlükten kaldırılmıştır.'}
        with patch.dict(site._YON_DEGISTIREN, {'g1': [degistiren]}, clear=True):
            site.degisiklik_listesi_ekle(hedef)
            site.son_degisiklik_bul(hedef)
        self.assertIn('Bölüm kaldırıldı', hedef['govde'])
        self.assertEqual(hedef['son_degisiklik'], '2011-10-19')  # metindeki kanun alıntısı sayılmaz
        belgeler = {b['id']: b for b in (kaldiran, mulga, notlu)}
        with patch.dict(site._KIMLIK, {i: (b['tur'], i) for i, b in belgeler.items()}, clear=True), \
                patch.dict(site._BELGE, belgeler, clear=True):
            site.mulga_son_degisiklik(belgeler)
        self.assertEqual(mulga['son_degisiklik'], '2024-12-04')
        self.assertEqual(notlu['son_degisiklik'], '2023-10-28')


    def test_zaman_isle_notlari(self):
        b = {'id': 'z', 'tur': 'kanun', 'tarih': '2008-01-01', 'govde': ''}
        h = ('<p class="madde" id="madde-2"><strong>EK MADDE 2 –</strong> (Ek: 11/8/2009-5921/3 md.; Değişik: 31/5/2012-6322/32 md.)</p>\n'
             '<p class="madde" id="madde-3"><strong>EK MADDE 3 –</strong> (Ek: 21/1/2010-5947/14 md.) (Mülga:26/7/2018-7146/12 md.)</p>\n'
             '<p>n) (Ek fıkra: 29/1/2016-6663/23 md.) Metin.</p>\n<p>Bir (Değişik ibare:RG-25/4/2023-32171) ibare ve (Ek-1) atfı.</p>')
        with patch.dict(site._BELGE, {}, clear=True), patch.dict(site._KIMLIK, {}, clear=True):
            cikti, veri = site.zaman_isle(b, h)
        import html as _h, json as _j, re as _re
        z = [[o[:4] for o in _j.loads(_h.unescape(x))] for x in _re.findall(r'data-z="([^"]*)"', cikti)]
        self.assertEqual(z[0], [['2009-08-11', 'e', '', 1], ['2012-05-31', 'd', '', 1]])
        self.assertEqual(z[1], [['2010-01-21', 'e', '', 1], ['2018-07-26', 'm', '', 1]])
        self.assertEqual(z[2], [['2016-01-29', 'e', 'fıkra', 2]])
        self.assertEqual(z[3], [['2023-04-25', 'd', 'ibare', 0]])
        self.assertIn('2018-07-26', veri['n'])


    def test_surum_talimat_cozumleme(self):
        import surum_olustur as so
        ilk = ("**MADDE 5 –** (1) Giriş.\n\n(2) Kadrolar:\n\na) Yönetim;\n\n1) Eski bir.\n\nç) İdari;\n\n1) Ayniyat.\n\n2) Eski iki.\n\n"
               "(3) Unvan:\n\na) Eski a.\n\n**GEÇİCİ MADDE 1 –** (1) Geçici.")
        b = so.Belge(ilk)
        ok, etk, _ = so.uygula2(b, "Aynı Yönetmeliğin 5 inci maddesinin ikinci fıkrasının (ç) bendinin (2) numaralı alt bendi ile "
                                   "üçüncü fıkrasının (a) bendi aşağıdaki şekilde değiştirilmiştir.", ["“2) Yeni iki.”", "“a) Yeni a.”"], "1/1/2020-1", {})
        metin = "\n".join(b.p)
        self.assertTrue(ok)
        self.assertIn("2) (Değişik:RG-1/1/2020-1) Yeni iki.", metin)
        self.assertIn("a) (Değişik:RG-1/1/2020-1) Yeni a.", metin)
        self.assertIn("1) Eski bir.", metin)
        self.assertEqual([m[0] for m in b.maddeler()], ["5", "gecici-1"])


if __name__ == '__main__':
    unittest.main()
