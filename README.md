# Canlı Sağlık Mevzuatı

Sağlık mevzuatını tek yerde toplayan, [mevzuat.gov.tr](https://www.mevzuat.gov.tr) benzeri açık bir mevzuat bilgi sistemi. Kanun, Cumhurbaşkanlığı kararnamesi ve yönetmeliklerin yanında Resmî Gazete'de yayımlanmayan **yönerge, genelge ve Sağlık Bakanlığı yazışmalarını** da içerir.

- Mevzuat türüne göre listeleme, başlıkta ve tam metinde arama, sayı ve yıl süzgeci
- Her tam metin için **Word (.docx)** ve **PDF** indirme, yazdırma ve metin içinde arama
- Tam metni henüz eklenmemiş düzenlemeler için künye ve resmî kaynağa bağlantı
- Resmî Gazete'yi her gün tarayan **Gemini 3.8 Flash** ajanı; bulduğu sağlık düzenlemelerini çekme isteği olarak önerir

Site GitHub Pages üzerinde statik olarak yayımlanır; sunucu veya veritabanı gerekmez.

## Kaynaklar

| Kaynak | İçerik |
| --- | --- |
| Halk Sağlığı Hizmetleri İzleme ve Değerlendirme Personeli için Mevzuat Kitabı (2025) | Kanun, KHK, CBK, tüzük, yönetmelik, yönerge, genelge, protokol ve Bakanlık yazıları |
| T.C. Sağlık Bakanlığı Yönergeler ve Genelgeler Kitabı (2025), Strateji Geliştirme Başkanlığı | Genel müdürlüklere göre Bakanlık yönergeleri ve genelgeleri |
| Özcan C, Temizer M. *Sağlık Mevzuatında 2020 Yılından Sonra Yapılan Değişiklikler* | 2020 sonrası yönetmelik, yönerge ve genelge listeleri |
| mevzuat.gov.tr, saglik.gov.tr, resmigazete.gov.tr | Künye bilgileri ve resmî bağlantılar |

## Klasör yapısı

```
icerik/<tür>/<id>.md          Tam metinler (YAML benzeri künye + Markdown)
kaynak-isleme/segmentler/     Kitaplardaki belgelerin sayfa aralıkları (ajan çıktısı)
kaynak-isleme/katalog/        Tam metni olmayan kayıtlar ve Resmî Gazete takibi
araclar/kitaptan_cikar.py     Segmentlere göre PDF'ten metin çıkarır
araclar/site_uret.py          Statik siteyi, Word ve PDF dosyalarını üretir
araclar/rg_takip.py           Resmî Gazete takip ajanı (Gemini 3.8 Flash)
site/assets/                  Stil, arama betiği, simge
```

## Yerelde çalıştırma

```bash
pip install -r requirements.txt
python araclar/site_uret.py            # _site/ klasörünü üretir
python -m http.server -d _site 8000    # http://localhost:8000
```

Kitaplardan metinleri yeniden çıkarmak için PDF'lerin bulunduğu klasörü verin:

```bash
python araclar/kitaptan_cikar.py --kaynak-dizin "/kitaplarin/klasoru"
```

## Yeni mevzuat ekleme

1. `icerik/<tür>/` altına künyesiyle bir `.md` dosyası ekleyin (örnekler için mevcut dosyalara bakın) ya da yalnızca künye için `kaynak-isleme/katalog/` altındaki bir JSON dosyasına kayıt ekleyin.
2. `main` dalına gönderin; site, Word ve PDF dosyaları otomatik üretilip yayımlanır.

Türler: `kanun`, `cbk`, `khk`, `tuzuk`, `yonetmelik`, `yonerge`, `genelge`, `teblig`, `protokol`, `yazi`.

## Resmî Gazete takibi

`.github/workflows/resmi-gazete.yml` her sabah Resmî Gazete'yi tarar. Depo ayarlarında **Settings → Secrets and variables → Actions** altında `GEMINI_API_KEY` tanımlanırsa Gemini 3.8 Flash ajanı her düzenlemenin sağlıkla ilgisini değerlendirir ve künyesini çıkarır; tanımlanmazsa anahtar sözcük süzgeci kullanılır. Model adı `GEMINI_MODEL` değişkeniyle değiştirilebilir.

## Uyarı

Bu site resmî bir kaynak değildir. Metinler basılı derlemelerden otomatik aktarılmıştır ve aktarım hataları içerebilir; hukuki işlemlerde Resmî Gazete ve ilgili kurumun yayımladığı metin esas alınmalıdır. Hata bildirimleri için konu (issue) açabilirsiniz.

