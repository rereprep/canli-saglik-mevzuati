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


if __name__ == '__main__':
    unittest.main()
