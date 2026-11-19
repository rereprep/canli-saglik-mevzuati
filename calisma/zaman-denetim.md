# Tarihe göre görüntüleme denetimi

19.11.2026 — Yalnız mevcut `_site` çıktısı ve üretim/gösterim kodu incelendi; mevzuatın resmî kaynaklarla veya yürürlük tarihleriyle bağımsız doğrulaması yapılmadı.

## Örneklem ve yöntem

Dört türün her birinde en büyük HTML dosyası alındı; kalanlar tür içinde sıralı dosya listesinden Python `random.seed(1947)` ile rastgele seçildi (4 kanun, 4 yönetmelik, 4 tebliğ, 3 yönerge). Bunlar dört belgeyi kasıtlı içerdiğinden tüm örneklem basit rastgele değildir. Python `HTMLParser` ile `p`/`h4` metinleri ve JSON olayları çözüldü; not, dipnot, tür, tarih ve madde sınırları örneklerle karşılaştırıldı. 15 dosyada toplam 2.596 olay kaydı sayıldı. İki yönerge yalnız yönlendirme sayfasıdır; dokuz sayfada olay kaydı yoktur. Bu nedenle yönergelerde olayların doğruluğu hakkında güçlü bir sonuç çıkarılamaz. Büyük dosyalarda bulgular örnekleme dayalıdır; tüm kayıtların tek tek hukuken doğrulandığı anlamına gelmez.

## Bulgular

1. **Bir parantez içindeki ikinci olay kayboluyor.** `kanun/k-sosyal-sigortalar-ve-genel-saglik-sigortasi-kanunu.html`, ek madde 2: `(Ek: 11/8/2009-5921/3 md.; Değişik: 31/5/2012-6322/32 md.)` için yalnız 2009 `e` kaydı var; 2012 değişikliği yok. Madde 78'de aynı sorun `(Ek cümle: …; İptal cümle: …)` içindeki iptal için de görülüyor. **Kural:** Parantezdeki her bağımsız tür/tarih çiftini ayrı olay olarak ayrıştır; noktalama ve iç içe parantezleri koru.
2. **İkinci tam madde olayı için bayrak kayıp.** Aynı kanun, ek madde 3: `(Ek: 21/1/2010-5947/14 md.) (Mülga:26/7/2018-7146/12 md.)` verisinde ekleme `tümMadde=1`, mülga `0`. İkisi de madde başındaki niteliksiz tam madde notu; konum hesabı yalnız ilk notu tam madde sayıyor. **Kural:** Madde etiketinden sonraki ardışık not kümesinde kapsamı her olay için ayrı belirle; önceki notların uzunluğunu engel sayma.
3. **Kanun tarihi yürürlük tarihi sanılıyor.** Aynı kanun, madde 6/c, dipnot `[12]`: olay `2014-09-10`, ancak dipnot değişikliğin **1/4/2015 tarihinde yürürlüğe girmek üzere** yapıldığını açıkça söylüyor. Benzer biçimde madde 60/e dipnotu 23/2/2017 tarihli kanunu ve 1/1/2018 yürürlüğünü ayrı belirtir. **Kural:** Tarihleri rolüyle ayır; açık yürürlük tarihini seç, yalnız kanun tarihi varsa yürürlüğü bilinmiyor olarak belirt. İlgili yürürlük hükümleri resmî kaynaktan ayrıca doğrulanmalı.
4. **Dipnot yanlış düzeyde gösteriliyor.** Aynı kanun, madde 9 girişindeki `[22]`: not, `(7), (8), (9) ve (10) numaralı alt bentler` içindeki ibarelerden söz ediyor; `data-z` ise yalnız madde giriş paragrafına bağlanmış. Kullanıcıya etkilenen alt bentler yerine girişte değişiklik gösteriliyor. **Kural:** Dipnot hedefinde açık alt bent/fıkra atıflarını ve yerel madde hiyerarşisini çöz; birden fazla hedef varsa her birine bağla, çözülemiyorsa madde düzeyinde belirsiz olarak göster.
5. **Çıkarılan ibare olay türü değişiklik olarak kaydediliyor.** Aynı kanun, madde 5/e dipnotu: `ibaresi madde metninden çıkarılmıştır` için `['2015-04-04','d','ibare',0,…]` var; madde 60/a/9 dipnotunda `yürürlükten kaldırılmış` ibaresi de `d`. **Kural:** Dipnottaki çıkarılma/kaldırılmayı `m`, iptali `i` olarak sınıflandır; `ibare` kapsamını koru ve kullanıcıya bütün bent kaldırılmış izlenimi verme.
6. **Yeniden düzenleme biçimi atlanıyor.** `teblig/k-sosyal-guvenlik-kurumu-saglik-uygulama-tebligi-sut.html`, 2.4.4.F-6 başlığı: `(Yeniden düzenleme:RG-9/9/2017-30175)` var, öğede `data-z` yok. **Kural:** `Yeniden düzenleme` notunu bağımsız değişiklik olayı olarak tanı; başlık ile izleyen hükümlerin kapsamını belge yapısından belirle.
7. **Eksik kapanan kaynak notu atlanıyor.** `yonetmelik/oz-turk-silahli-kuvvetleri-jandarma-genel-komutanligi-ve-sahil-guvenlik-komutanligi-2016-11-11.html`, hastalıklar listesi, kulak işitme kayıpları D/1: `(Değişik:RG-15/4/2020-31100-C.K-2413/25 md` kapanış parantezi olmadan devam ediyor; `data-z` yok. **Kural:** Kaynak kusurunu raporla; tarih ve karar künyesi güvenle ayrılabiliyorsa kontrollü tolerans uygula, aksi halde inceleme kuyruğuna al. Parantez onarımı varsayımla sessizce yapılmamalı.
8. **Kısmi ekleme bütün paragrafı yok sayabiliyor.** Aynı kanun, madde 6/n, `n) (Ek fıkra: 29/1/2016-6663/23 md.)` olayı `e/fıkra/0`; mevcut gösterim `e` ve `fıkra` için tüm HTML paragrafına “bu hüküm yoktu” sınıfı uyguluyor. Diğer olaylarda paragraf içinde birden fazla hüküm bulunabildiğinden, olay kapsamı ile HTML blok kapsamı eşleşmediğinde aynı sorun oluşabilir. **Kural:** Etkilenen fıkra/bent sınırı kesin belirlenemiyorsa yalnız değişiklik uyarısı ver; kısmi olay için tüm paragrafı yok sayma. Bu örnekte kaynak notunun “fıkra” ile bent gösterimi arasındaki uyumsuzluk ayrıca kontrol edilmeli.

Alıntılanan başka mevzuata ait notların yanlış olay sayılması açısından örnekler tarandı; bu örneklemde rapora alınacak kesin bir örnek doğrulanmadı. Bu durum böyle hata olmadığı anlamına gelmez.

## Seçilen dosyalar

Yollar `_site/mevzuat/` altındadır; parantez içi sayılar çözülen olay sayısıdır.

- `kanun/k-sosyal-sigortalar-ve-genel-saglik-sigortasi-kanunu.html` (757)
- `kanun/sbg-10401-sitma-ve-frengi-ilaclari-hakkinda-kanun.html` (0)
- `kanun/k-radiyoloji-radiyom-ve-elektrikle-tedavi-ve-diger-fizyoterapi-muesseseleri-hakkinda-kanun.html` (10)
- `kanun/sbg-10403-verem-savasi-hakkinda-kanun.html` (0)
- `yonetmelik/oz-turk-silahli-kuvvetleri-jandarma-genel-komutanligi-ve-sahil-guvenlik-komutanligi-2016-11-11.html` (243)
- `yonetmelik/oz-ithal-edilecek-ilac-ham-baslangic-maddeleri-ispenciyari-ve-tibbi-mustahzarlar-yo-1984-11-01.html` (0)
- `yonetmelik/oz-yanik-tedavi-birimleri-hakkinda-yonetmelik-2019-10-08.html` (0)
- `yonetmelik/toplum-sagligi-merkezi-ve-bagli-birimler-yonetmeligi.html` (26)
- `teblig/k-sosyal-guvenlik-kurumu-saglik-uygulama-tebligi-sut.html` (1556)
- `teblig/sbg-11314-gida-maddelerindeki-bulasanlarin-maksimum-limitleri-hakkinda-teblig-20.html` (0)
- `teblig/sbg-11338-peloidlerin-uretimi-ve-satisi-hakkinda-teblig.html` (4)
- `teblig/sbg-11313-turk-gida-kodeksi-devam-formulleri.html` (0)
- `yonerge/sbg-11257-saglik-bakanligi-yangin-onleme-ve-sondurme-yonergesi.html` (0)
- `yonerge/aile-hekimligi-tarama-ve-takip-katsayisina-iliskin-yonerge.html` (0; yönlendirme)
- `yonerge/sbg-103799-merkez-pay-yonergesi.html` (0; yönlendirme)
