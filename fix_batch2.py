import os, re

# ==================== DOSYA 6 ====================
fpath6 = "/Users/mithattemizer/Documents/Canlı Sağlık Mevzuatı/canli-saglik-mevzuati/icerik/genelge/sb-kizamik-kizamikcik-ve-konjenital-kizamikcik-sendromu-kks-genelgesi-2010-20.md"
with open(fpath6, 'r', encoding='utf-8') as f:
    text6 = f.read()

parts6 = text6.split('---', 2)
body6 = parts6[2].strip()

fm6 = """---
id: "sb-kizamik-kizamikcik-ve-konjenital-kizamikcik-sendromu-kks-genelgesi-2010-20"
baslik: "Kızamık/Kızamıkcık ve Konjenital Kızamıkçık Sendromu (KKS) Genelgesi (2010/20)"
tur: "genelge"
sayi: "2010/20"
tarih: "2010-04-01"
birim: "Temel Sağlık Hizmetleri Genel Müdürlüğü"
konu: "Kızamık, kızamıkçık ve konjenital kızamıkçık sendromu (KKS) eliminasyon hedefleri doğrultusunda vaka bazlı sürveyans ve aşı uygulamalarını düzenler."
etiketler: ["halk sağlığı", "aşı", "kızamık", "bulaşıcı hastalıklar"]
kaynak: "Sağlık Bakanlığı Yönergeler ve Genelgeler Kitabı (2025), s. 525-563"
durum: "yürürlükte"
ocr: true
duzeltildi: true
---"""

if "Kızamık ve Kızamıkçığın Eliminasyonu ve KKS'nin Önlenmesi Programı hazırlanmıştır" not in body6:
    header_page525 = """6.3.15. Kızamık/Kızamıkcık ve Konjenital Kızamıkçık Sendromu (KKS) Genelgesi (2010/20)

### T.C. SAĞLIK BAKANLIĞI
Temel Sağlık Hizmetleri Genel Müdürlüğü

Sayı: B100TSH01105 / 18617
Tarih: 01.04.2010
Konu: Kızamık/Kızamıkçık ve Konjenital Kızamıkçık Sendromu (KKS) Sürveyansı Genelgesi

GENELGE 2010/20

Türkiye'de kızamığa bağlı morbidite ve mortalitenin yüksekliği ve Dünyada ve Avrupa bölgesinde son yıllarda kaydedilen gelişmeler ve deneyimler de göz önüne alınarak, 2002-2010 yıllarını kapsayan Kızamık ve Kızamıkçığın Eliminasyonu ve KKS'nin Önlenmesi Programı hazırlanmıştır. Programın amacı Türkiye'de kızamık ve kızamıkçık hastalıklarını elimine etmek, KKS'yi önlemek ve bu düzeyleri sürdürmektir. 2002 yılında %82 olan kızamık aşılama hızı, yürütülen başarılı bağışıklama çalışmalarıyla 2009 yılında %97'ye yükselmiştir. Hedefimiz, 2010 yılı sonuna kadar Türkiye'de yerli virüs geçişini durdurmak, 2010 yılından sonra Türkiye dışından gelecek yeni kızamık virüslerinin Türkiye'de yerleşmesini önlemek ve kızamığa bağlı ölümleri engellemektir.

Programın temel stratejilerinden biri de destek aşılama çalışması sonrasında kızamık insidansının azalması ile vaka bazında, laboratuvar destekli kızamık sürveyansına geçilmesi ve akut flask paralizi sürveyansına entegre edilmiş haftalık aktif sürveyansın oluşturulması olarak belirlenmiştir. “Kızamık Eliminasyon Programı, Kızamık Saha Rehberi”nde laboratuvar destekli ve vaka bazlı kızamık sürveyansı kuralları belirlenmiştir. 2005 yılında da Bulaşıcı Hastalıkların İhbarı ve Bildirim Sistemi Yönergesi ile laboratuvar destekli standart vaka tanımları yapılarak bildirimin kuralları belirlenmiştir.

Programın stratejik hedeflerine uygun olarak rutin aşılama hızının %95'in üzerinde olması ve destek aşılama çalışmalarının başarıyla tamamlanması sonucunda kızamık vaka sayımız da giderek azalmış, 2001 yılında 30.509 iken, 2009 yılında 4'e (3 importe, 1 importe vaka ile ilişkili vaka) kadar düşmüştür. Böylece eliminasyon dönemine geçilerek importasyonun engellenmesi giderek daha da ön plana çıkan bir hedef haline gelmiştir. Eliminasyon döneminde yürütülecek sürveyansa özgü bazı farklılıklar bulunmaktadır.

Eliminasyon döneminde, kızamık sürveyansı stratejilerimiz şunlardır:

a. Rutin bildirimlerin tam, zamanında, doğru ve tutarlı olmasının sağlanması,
b. Aktif sürveyans yürütülmesi,
c. Vaka bazında, laboratuvar destekli sürveyansın sürdürülmesi,
d. Aşı sonrası istenmeyen etki sürveyansı ile bağışıklama güvenliğinin izlenmesi,
e. Rutin bağışıklama hızlarıyla programın sürekli izlenmesi ve değerlendirilmesi,
f. Salgınların erken saptanması, incelenmesi, doğrulanmasını ve elde edilen verilerin salgınların kontrolü ve önlenmesi stratejilerini belirlenmesinde kullanılması ve gerekiyorsa seroprevalans araştırmaları ile hassas nüfus birikimine ilişkin bilgi sağlanması,
g. Vaka ve salgın doğrulaması için oluşturulmuş olan bir laboratuvar ağının geliştirilmesidir.

### T.C. SAĞLIK BAKANLIĞI
Temel Sağlık Hizmetleri Genel Müdürlüğü

"""
    idx_turkiye = body6.find("Türkiye'de kızamik sürveyansuun")
    if idx_turkiye != -1:
        body6 = header_page525 + body6[idx_turkiye:]

body6 = re.sub(r'T.C.s+SAĞLIKs+BAKANLIĞIs+YÖNERGELERs+VEs+GENELGELERs+KİTABI', '', body6, flags=re.IGNORECASE)
body6 = re.sub(r'^s*d+s*$', '', body6, flags=re.MULTILINE)

fixes6 = [
    ("kızamik", "kızamık"),
    ("sürveyansuun", "sürveyansının"),
    ("ulaşıldıgmım kamlarast", "ulaşıldığının kanıtlanması"),
    ("otusı", "olası"),
    ("tespui", "tespiti"),
    ("salgı yanıtı", "salgın yanıtı"),
    ("kontol ahıne aimmasina", "kontrol altına alınmasını"),
    ("amacyla veniden düzenlenmış", "amacıyla yeniden düzenlenmiş"),
    ("sırısında", "sırasında"),
    ("kurallan", "kuralları"),
    ("Daimi Genelge ekte gönderilmektedir. Bu Daimi Genelge yaymdanlığr tarihte yürdebEe girer.", "Daimi Genelge ekte gönderilmektedir. Bu Daimi Genelge yayımlandığı tarihte yürürlüğe girer."),
    ("Kızanık/Kizamıkçık/KKS", "Kızamık/Kızamıkçık/KKS"),
    ("kaynagı ofan bu Daimı Genelke har düzeyde", "kaynağı olan bu Daimi Genelge her düzeyde"),
    ("tum sağlık çalişanlarınım", "tüm sağlık çalışanlarının"),
    ("uygulamadakı değişiklikleri yakındın", "uygulamadaki değişiklikleri yakından"),
    ("Kozamık Süreyanai Dami Genelgesinin", "Kızamık Sürveyansı Daimi Genelgesinin"),
    ("sağlık kuruluşlarma (Tip Paknheleri", "sağlık kuruluşlarına (Tıp Fakülteleri"),
    ("Özel Sağlık Küralışlary ve Mugyenelaneler dähili", "Özel Sağlık Kuruluşları ve Muayenehaneler dâhil)"),
    ("karşılğı tebligaui ve il duzeyinde", "karşılığı tebligatı ve il düzeyinde"),
    ("uygulamalann Genclgeye uygun olarak yürütülmesi hususunda gerggini onemle rica ederim-", "uygulamaların Genelgeye uygun olarak yürütülmesi hususunda gereğini önemle rica ederim."),
    ("Müstesar 1K Daimi Geneluc", "Müsteşar\n\nEK: Daimi Genelge"),
    ("Otkemizde", "Ülkemizde"),
    ("Sağlık Orgüti", "Sağlık Örgütü"),
    ("yıhnda", "yılında"),
    ("başanıyla", "başarıyla"),
    ("așılama huzma", "aşılama hızına"),
    ("Aynıca", "Ayrıca"),
    ("tamamlanmışır", "tamamlanmıştır"),
    ("kadılara yönelik", "kadınlara yönelik"),
    ("Her iki progranda da hedef; 2010 yılı\n\nBu durumun", "Her iki programda da hedef; 2010 yılı sonuna kadar ülkemizde yerli virüs dolaşımını durdurmaktır.\n\nBu durumun"),
    ("çalışmalan", "çalışmaları"),
    ("yayınlanan DSO", "yayınlanan DSÖ"),
    ("dikkate ahınarak hazırlanan bu Genelge ile ülkemizdeki süreyans çahşmalanun", "dikkate alınarak hazırlanan bu Genelge ile ülkemizdeki sürveyans çalışmalarının"),
    ("kazamakçığın", "kızamıkçığın"),
    ("KIZAMIK, KIZAMIKÇIK VE KONJENITAL KIZAMIKÇIK SENDROMU SÜRVEYANSI DAİMİ GENELGESİ GİRİŞ", "### KIZAMIK, KIZAMIKÇIK VE KONJENİTAL KIZAMIKÇIK SENDROMU SÜRVEYANSI DAİMİ GENELGESİ\n\n### GİRİŞ"),
    ("Dünya Sağlık Orgütü", "Dünya Sağlık Örgütü"),
    ("Aşilama HIZI", "Aşılama Hızı"),
    ("kapsayıcılığa\n\n2.", "kapsayıcılığa ulaşılmasıdır.\n\n2."),
    ("Kizamık/Kızamıkçık İnsidans Hıza", "Kızamık/Kızamıkçık İnsidans Hızı"),
    ("insidansıun", "insidansının"),
    ("bulunmadığımı", "bulunmadığını"),
    ("Insidans Hızı", "İnsidans Hızı"),
    ("1 den daha az", "1'den daha az"),
    ("pidemiyolojik", "epidemiyolojik"),
    ("sınırhı", "sınırlı"),
    ("tanımlanmıştır, a.", "tanımlanmıştır:\n\na."),
    ("Yuksek", "Yüksek"),
    ("kapsayıcıhğı", "kapsayıcılığı"),
    ("saptanmistar", "saptanmıştır")
]

for src, dst in fixes6:
    body6 = body6.replace(src, dst)

body6 = re.sub(r'\n{3,}', '\n\n', body6)

with open(fpath6, 'w', encoding='utf-8') as f:
    f.write(fm6 + "\n\n" + body6 + "\n")
print("Dosya 6 güncellendi.")

# ==================== DOSYA 7 ====================
fpath7 = "/Users/mithattemizer/Documents/Canlı Sağlık Mevzuatı/canli-saglik-mevzuati/icerik/genelge/sb-klinik-kalite-uygulama-ve-veri-kalitesi-iyilestirme-rehberi-genelgesi-2019-15.md"
content7 = """---
id: "sb-klinik-kalite-uygulama-ve-veri-kalitesi-iyilestirme-rehberi-genelgesi-2019-15"
baslik: "Klinik Kalite Uygulama ve Veri Kalitesi İyileştirme Rehberi Genelgesi (2019/15)"
tur: "genelge"
sayi: "2019/15"
tarih: "2019-07-22"
birim: "Sağlık Hizmetleri Genel Müdürlüğü"
konu: "Klinik kalite ölçme ve değerlendirme sistemi ile sağlıkta veri kalitesinin iyileştirilmesine yönelik rehber esaslarını belirler."
etiketler: ["klinik kalite", "veri kalitesi", "e-nabız", "rehber"]
kaynak: "Sağlık Bakanlığı Yönergeler ve Genelgeler Kitabı (2025), s. 168-169"
durum: "yürürlükte"
ocr: true
duzeltildi: true
---

2.3.12. Klinik Kalite Uygulama ve Veri Kalitesi İyileştirme Rehberi Genelgesi (2019/15)

### T.C. SAĞLIK BAKANLIĞI
Sağlık Hizmetleri Genel Müdürlüğü

Sayı : 54567092-010.06.02
Konu : Klinik Kalite Uygulama ve Veri Kalitesi İyileştirme Rehberi

GENELGE
2019/ 15

İlgi : 22/05/2017 tarih ve 64047795 – 010.06.01 – E.01-212 sayılı Genelge (2017/8)

Bakanlığımızca Sağlıkta Dönüşüm Programı ile birlikte nitelikli ve etkili sağlık hizmeti için kalite ve akreditasyon faaliyetlerine başlanmış ve ülke genelinde bu alanda önemli bir mesafe kat edilmiştir. Bu kapsamda kalite ve akreditasyon faaliyetleri bünyesinde, teşhis tedavi ve bakım süreçlerinin iyileştirilmesi amacıyla Türkiye Klinik Kalite Ölçme ve Değerlendirme Sistemi’nin kurulmasına yönelik çalışmalar başlatılmıştır.

Sistem, hastalık yükü, ölçülebilirlik ve süreçlere müdahale ile iyileştirmeye açık olma özelliği dikkate alınarak, belirlenen sağlık olgularına yönelik tıbbi süreçler ve klinik sonuçların kurumsal, bölgesel ve ulusal düzeyde izlenmesi, analiz edilmesi ve iyileştirilmesini amaçlamaktadır. Sistem kapsamında sağlık olgusu ve göstergeler belirlenmiş, söz konusu göstergelere ilişkin verilerin elde edilmesi amacıyla E-Nabız üzerinde Klinik Kalite Karar Destek Sistemi oluşturulmuştur.

Gösterge sonuçlarına yönelik analizlerin doğru yapılması ve iyileştirmeye açık alanların doğru şekilde belirlenmesi için sistemden doğru verilerin elde edilmesi büyük önem arz etmektedir. Bu bağlamda, takip edilen sağlık olgularına dair klinik süreçlerin kalitesi ile ilgili sorumluların ve sorumlulukların tanımlanması, elde edilen verilerin doğrulanması ve veri kalitesinin iyileştirilmesine yönelik sağlık kuruluşlarında gerçekleştirilmesi gereken faaliyetlere ilişkin “Klinik Kalite Uygulama ve Veri Kalitesi İyileştirme Rehberi” hazırlanmış ve 22/05/2017 tarihli Bakanlık Onayı ile 2017/8 sayılı Genelge’nin eki olarak yayınlanmıştı. 25 Ağustos 2017 tarihli Resmî Gazetede yayımlanan 694 sayılı Kanun Hükmünde Kararname ve bunun akabinde, 10/7/2018 tarihli Resmî Gazete’de yayımlanan 1 sayılı Cumhurbaşkanlığı Teşkilatı Hakkında Cumhurbaşkanlığı Kararnamesi ile Sağlık Bakanlığının teşkilat yapısında bir kısım değişiklikler yapılmıştır. Yapılan değişikliklerin klinik kalite kurumsal yapısında da değişiklik yapılmasını gerektirmesi sebebiyle söz konusu rehber güncellenmiştir. Güncel rehbere http://kalite.saglik.gov.tr/ ve http://klinikkalite.saglik.gov.tr/ adreslerinden ulaşılabilmektedir. Bu genelgenin yürürlüğe girdiği tarihten itibaren, ilgide kayıtlı Genelge yürürlükten kaldırılmıştır.

Bilgilerinizi ve uygulamaların ekteki rehbere uygun olarak yürütülmesi gerektiğinin ilgili tüm kamu ve özel sağlık hizmet sunucularına tebliğini önemle rica ederim.

Dr. Fahrettin KOCA
Bakan

EK: Klinik Kalite Uygulama ve Veri Kalitesi İyileştirme Rehberi (28 s.)

DAĞITIM:
81 İl Valiliği
Yüksek Öğretim Kurulu (YÖK) Başkanlığına
"""
with open(fpath7, 'w', encoding='utf-8') as f:
    f.write(content7.strip() + '\n')
print("Dosya 7 güncellendi.")

# ==================== DOSYA 8 ====================
fpath8 = "/Users/mithattemizer/Documents/Canlı Sağlık Mevzuatı/canli-saglik-mevzuati/icerik/genelge/sb-kok-hucre-calismalari-genelgesi-2006-51.md"
content8 = """---
id: "sb-kok-hucre-calismalari-genelgesi-2006-51"
baslik: "Kök Hücre Çalışmaları Genelgesi (2006/51)"
tur: "genelge"
sayi: "2006/51"
tarih: "2006-05-01"
birim: "Tedavi Hizmetleri Genel Müdürlüğü"
konu: "Kök hücre araştırmaları ve klinik uygulamalarında etik kurul onayları ile uygulama kriterlerini düzenler."
etiketler: ["kök hücre", "klinik araştırma", "etik kurul"]
kaynak: "Sağlık Bakanlığı Yönergeler ve Genelgeler Kitabı (2025), s. 278-280"
durum: "yürürlükte"
ocr: true
duzeltildi: true
---

2.3.54. Kök Hücre Çalışmaları Genelgesi (2006/51)

### T.C. SAĞLIK BAKANLIĞI
Tedavi Hizmetleri Genel Müdürlüğü

Sayı : B.10.0.THG.0.14.00.03- / 8647
Tarih: 01.05.2006
Konu : Kök Hücre Çalışmaları

....................VALİLİĞİNE
(İl Sağlık Müdürlüğü)

GENELGE
2006 / 51

Kök hücre nakli özellikle hematolojik, onkolojik hastalıklarda bir tedavi yöntemi olarak uzun yıllardır kullanılmaktadır. Son yıllarda farklı hastalıklarda da tedavi amaçlı kök hücre kullanımı gündeme gelmiştir. Dünyada ve ülkemizde kök hücre nakli ile tedavi konusunda halen yoğun araştırmalar yapılmakta olup, konu ile ilgili haberler basın ve yayın organlarında sıklıkla yer almaktadır. Bazı hastalıkların tedavisinde ümit verici bir yöntem olarak değerlendirilmesine karşın, henüz kök hücre nakli yapılan hasta sayısı çok azdır ve uygulamanın başarısı veya uzun vadede tedavinin hastada meydana getirebileceği yan etkiler konusunda yeterli bilgi mevcut değildir.

Bakanlığımızca; kök hücre nakli çalışmalarıyla ilgili olarak, çalışmanın yapılacağı kurum bünyesinde gerekli altyapının oluşturulması ve çağdaş bilimin gereklerine uygun olarak uygulama yapılabilmesi amacıyla Kök Hücre Nakilleri Bilimsel Danışma Kurulu oluşturulmuş ve “Klinik Amaçlı Embriyonik Olmayan Kök Hücre Çalışmaları Kılavuzu” hazırlanmıştır. Ekte gönderilmekte olan Kılavuzun gereğinin ifası için, konu ile ilgili tüm kamu ve özel kurum-kuruluşlar ile üniversiteler bünyesindeki ilgili personele tebliğini önemle rica ederim.

Prof. Dr. Recep AKDAĞ
Bakan

Ek: 2

### KLİNİK AMAÇLI EMBRİYONİK OLMAYAN KÖK HÜCRE ÇALIŞMALARI KILAVUZU

**Giriş:**

Bu kılavuz ülkemizde, mevcut medikal veya cerrahi tedavi yöntemleriyle tedavisi başarısız olmuş hastalarda klinik amaçlı, insan kaynaklı embriyonik olmayan kök hücre çalışmalarında uyulması gereken esasların düzenlenmesi amacıyla hazırlanmıştır.

**Çalışmanın Uygulanabileceği Hastaneler:**

Klinik amaçlı embriyonik olmayan kök hücre çalışmaları T.C. Sağlık Bakanlığı'nca kurulmuş olan “Kök Hücre Nakilleri Bilimsel Danışma Kurulu” tarafından değerlendirilerek, Bakanlıkça bu alanda çalışmasına onay verilen bilimsel merkezlerde yapılır. Bu merkezlerin kök hücre çalışması yapmak üzere bilimsel kurula başvururken bu konuda gereken temel bilgi, beceri ve donanıma sahip olduklarını kanıtlayan verileri sunmaları gereklidir.

Başvuru yapacak merkezin; ilgili dallarda kadrolu uzman tabip çalıştırmak suretiyle sağlık hizmeti veren; hasta kabul ve tedavi ettiği uzmanlık dalları için gerekli ve günün gelişmiş tıp teknolojisine uygun olan diğer bütün teşhis ve tedavi birimlerini ve ayrıca asgari radyoloji ünitesi ile biyokimya, mikrobiyoloji, kök hücre tanımlaması, sayımı, çoğaltılması ve ayrıştırması yapabilen hematoloji, immünoloji ve patoloji laboratuvarlarını bünyesinde bulunduran bir kurum olması gereklidir.

Kök Hücre Nakilleri Bilimsel Danışma Kurulu bu özellikleri taşıyan bilimsel merkezlerin daha önce yapmış olduğu hayvan deneyleri, ürettikleri bilimsel çalışmalar, yaptıkları yayınlar ve merkezde çalışan bilim insanlarının bu konudaki birikimini içeren kriterleri göz önüne alarak değerlendirmesini yapar.

**Çalışmanın Yürütülme Şekli:**

Klinik amaçlı çalışmanın planlandığı kurum bünyesinde, kök hücre çalışmalarına yönelik olarak kurulacak “yerel etik kurul” onayını takiben, çalışma başvuru dosyası Kök Hücre Nakilleri Bilimsel Danışma Kurulu'na sunulur. Kurulun incelemesini müteakip Bakanlıkça izin verilmesi kaydıyla çalışma gerçekleştirilir. Kök Hücre Nakilleri Bilimsel Danışma Kurulu'na başvuru esnasında, çalışmaya ilişkin ayrıntılı bilgilerin yanısıra, hastalara verilecek olan “bilgilendirilmiş gönüllü olur formu” taslağının da dosyaya eklenmesi gereklidir. Hastada bu uygulama sırasında ya da sonrasında gelişebilecek istenmeyen veya beklenmeyen etkilerin önlenmesi için gerekli tedbirlerin alınması ve komplikasyonların telafi/tedavisi için güvence sağlanması (sigorta edilmesi) ardından çalışma başlatılır.

Klinik kök hücre çalışmalarının başlatılabilmesi için:

a) Benzer çalışmanın öncelikle insan dışı deney ortamında veya yeterli sayıda hayvan üzerinde yapılmış olması,
b) İnsan dışı deney ortamında veya hayvanlar üzerinde yapılan deneyler sonucunda ulaşılan bilimsel verilerin, varılmak istenen hedefe ulaşmak açısından bunların insan üzerinde de yapılmasını gerekli kılması,
c) Çalışmanın, insan sağlığı üzerinde öngörülebilir zararlı ve kalıcı bir etki bırakmaması, gerekir.

**Sağlık Bakanlığı'na Bildirim:**

Kök Hücre Nakilleri Bilimsel Danışma Kurulu tarafından onay verilmiş olan çalışmaların, 6 ayda bir gelişme raporlarının ve çalışma sonrasında “Sonuç Raporunun” Sağlık Bakanlığı'na bildirilmesi zorunludur. Rapor içeriğinde, çalışma yapılan hastanın:

- Adı Soyadı,
- Yaşı,
- Cinsiyeti,
- Tanısı,
- Evresi,
- Daha önce uygulanan tedaviler,
- Kök hücre kaynağı, miktarı, uygulama yolu,
- Ek tedaviler,
- Tedavi sonucu,
- Gözlem ve öneriler, ayrıntılı biçimde belirtilmelidir.

Çalışmayı yapan kurum, hastanın takibinde oluşabilecek beklenmeyen ciddi yan etkilerin veya ölüm durumunun ortaya çıkması halinde, yedi gün içinde sebeplerine yönelik bilgilerle, komplikasyonların ayrıntılı dökümünü Sağlık Bakanlığı'na bildirir.

Klinik kök hücre çalışması tamamlanıp, sonuçları bilimsel bir ortamda veya hakemli bilimsel bir dergide yayınlanmadıkça söz konusu çalışma ile ilgili verilerin kamuoyunu yönlendirecek/yanıltacak biçimde açıklanması yasaktır.

Hasta hakları ve insan onuruna saygı gereği, hastalarla ilgili bilgilerde mahremiyet hakkının gözetilmesi ve tıp etiğine uyulması esastır.
"""
with open(fpath8, 'w', encoding='utf-8') as f:
    f.write(content8.strip() + '\n')
print("Dosya 8 güncellendi.")

# ==================== DOSYA 9 ====================
fpath9 = "/Users/mithattemizer/Documents/Canlı Sağlık Mevzuatı/canli-saglik-mevzuati/icerik/genelge/sb-konaklama-tesisleri-bunyesinde-sunulacak-saglik-hizmetleri-genelgesi-2013-18.md"
with open(fpath9, 'r', encoding='utf-8') as f:
    text9 = f.read()

parts9 = text9.split('---', 2)
body9 = parts9[2].strip()

fm9 = """---
id: "sb-konaklama-tesisleri-bunyesinde-sunulacak-saglik-hizmetleri-genelgesi-2013-18"
baslik: "Konaklama Tesisleri Bünyesinde Sunulacak Sağlık Hizmetleri Genelgesi (2013/18)"
tur: "genelge"
sayi: "2013/18"
tarih: "2013-09-26"
birim: "Sağlık Hizmetleri Genel Müdürlüğü"
konu: "Konaklama tesisleri bünyesinde açılacak sağlık ünitelerinin kuruluş, başvuru, personel ve işleyiş şartlarını düzenler."
etiketler: ["özel sağlık kuruluşları", "konaklama tesisleri", "sağlık ünitesi", "turizm"]
kaynak: "Sağlık Bakanlığı Yönergeler ve Genelgeler Kitabı (2025), s. 263-267"
durum: "yürürlükte"
ocr: true
duzeltildi: true
---"""

header_page263 = """2.3.48. Konaklama Tesisleri Bünyesinde Sunulacak Sağlık Hizmetleri Genelgesi (2013/18)

### T.C. SAĞLIK BAKANLIĞI
Sağlık Hizmetleri Genel Müdürlüğü

Sayı : 54567092/010.06/ 32724
Tarih: 26.09.2013
Konu : Konaklama Tesisleri Bünyesinde Sunulacak Sağlık Hizmetleri

..................... VALİLİĞİNE
(İl Sağlık Müdürlüğü)

GENELGE
2013/18

Özel Hastaneler Yönetmeliğinin Ek 10 uncu maddesi ile Ayakta Teşhis ve Tedavi Yapılan Özel Sağlık Kuruluşları Hakkında Yönetmeliğin Ek 2 nci maddesi ve Diyaliz Merkezleri Hakkında Yönetmeliğin Ek 1 inci maddesinde "Konaklama tesislerinde sunulacak sağlık hizmetleri" ile ilgili düzenleme yapılmıştır.
Kültür ve Turizm Bakanlığından belgeli konaklama tesislerinde sunulacak sağlık hizmetleri, sağlık ünitelerinin ve birimlerin kuruluş ve işleyişine dair aşağıdaki açıklamaların yapılmasında fayda görülmüştür.

A. Bu Genelgede geçen;
a) Bakanlık: Sağlık Bakanlığını,
b) Konaklama tesisi: Kültür ve Turizm Bakanlığından işletme veya yatırım belgesi almış tesisleri,
c) Müdürlük: İl Sağlık Müdürlüğünü,
d) Özel sağlık kuruluşu: Sağlık hizmeti sunmak üzere Sağlık Bakanlığınca veya müdürlükçe ruhsatlandırılmış özel sağlık kuruluşlarını,
e) Sağlık ünitesi: Konaklama tesisinde konaklayan kişilerin ani gelişen sağlık problemlerinde ve acil durumlarda müdahale, muayene ve sevk işlemlerinin düzenlenmesi amacıyla konaklama tesislerinde kurulan birimleri,
f) Turizm yatırım belgesi: Konaklama tesisi açmak için ilk müracaatta Kültür ve Turizm Bakanlığınca yatırımcıya verilen belgeyi,
g) Turizm işletme belgesi: Konaklama tesisi işletmek için Kültür ve Turizm Bakanlığınca yatırımcıya verilen belgeyi,
h) Yönetmelik: Özel Hastaneler Yönetmeliği ile Ayakta Teşhis ve Tedavi Yapılan Özel Sağlık Kuruluşları Hakkında Yönetmeliği ve Diyaliz Merkezleri Hakkında Yönetmeliği,
ifade eder.

B. Konaklama tesisinde açılacak sağlık üniteleri başvuruları ve işleyişi
1) Sağlık ünitesi işletecekler; konaklama tesisinin bulunduğu ilde faaliyet gösteren herhangi bir özel sağlık kuruluşuna bağlı olarak, bu özel sağlık kuruluşunun kadro ve kapasitesini kullanarak başvuru yapabilir. Bir özel sağlık kuruluşu, en fazla kadrolu hekim sayısı kadar konaklama tesisinde sağlık ünitesi açabilir.
2) Bir özel sağlık kuruluşuna bağlı olarak işletilecek sağlık ünitelerinin tüm faaliyetlerinden bağlı olduğu sağlık kuruluşu sorumludur.
"""

if "Özel Hastaneler Yönetmeliğinin Ek 10 uncu maddesi" not in body9:
    idx_m3 = body9.find("3) Bağımsız olarak açılmak istenen")
    if idx_m3 != -1:
        body9 = header_page263 + "\n" + body9[idx_m3:]

body9 = re.sub(r'T.C.s+SAĞLIKs+BAKANLIĞIs+YÖNERGELERs+VEs+GENELGELERs+KİTABI', '', body9, flags=re.IGNORECASE)
body9 = re.sub(r'TCs+Sağliks+Bekanegs+Sağlıks+Hizmetleris+Genels+Müdürlüğü', '', body9)

fixes9 = [
    ("bağhı", "bağlı"),
    ("başvurulanı", "başvuruları"),
    ("tarafindan", "tarafından"),
    ("Sağhk", "Sağlık"),
    ("Çalişma", "Çalışma"),
    ("Dağitım: 81 Il Valiligi", "DAĞITIM:\n81 İl Valiliğine")
]
for src, dst in fixes9:
    body9 = body9.replace(src, dst)

body9 = re.sub(r'\n{3,}', '\n\n', body9)

with open(fpath9, 'w', encoding='utf-8') as f:
    f.write(fm9 + "\n\n" + body9 + "\n")
print("Dosya 9 güncellendi.")

# ==================== DOSYA 10 ====================
fpath10 = "/Users/mithattemizer/Documents/Canlı Sağlık Mevzuatı/canli-saglik-mevzuati/icerik/genelge/sb-kritik-kan-stok-seviyesinin-korunmasi-genelgesi-2013-24.md"
content10 = """---
id: "sb-kritik-kan-stok-seviyesinin-korunmasi-genelgesi-2013-24"
baslik: "Kritik Kan Stok Seviyesinin Korunması Genelgesi (2013/24)"
tur: "genelge"
sayi: "2013/24"
tarih: "2013-12-25"
birim: "Sağlık Hizmetleri Genel Müdürlüğü"
konu: "Sağlık tesislerinde acil ve rutin kan ihtiyacını karşılamak üzere kritik kan stok seviyelerinin korunmasını düzenler."
etiketler: ["kan hizmetleri", "transfüzyon merkezi", "kan bankacılığı", "kızılay"]
kaynak: "Sağlık Bakanlığı Yönergeler ve Genelgeler Kitabı (2025), s. 174-174"
durum: "yürürlükte"
ocr: true
duzeltildi: true
---

2.3.14. Kritik Kan Stok Seviyesinin Korunması Genelgesi (2013/24)

### T.C. SAĞLIK BAKANLIĞI
Sağlık Hizmetleri Genel Müdürlüğü

Sayı : 74831629/210/2013.5363.42803
Tarih: 25.12.2013
Konu : Kritik Kan Stok Seviyesinin Korunması

GENELGE
2013/24

Hastane transfüzyon merkezlerinde düzenli olarak bulundurulan kan ve kan bileşeni stoklarının kritik seviyelerinin korunması başta gebelik ve riskli doğumlar olmak üzere acil kan ve kan bileşenine ihtiyaç duyulan vakalarda, hayat kurtarıcı bir destek sağlamaktadır. Sınırlı bir kaynak olan kan ve kan bileşenlerine, ihtiyaç halinde hızlı bir şekilde ulaşabilmek amacıyla stokların kritik seviyelerinin belirlenmesi ve korunması bölgesel kan bankacılığı sistemimiz açısından büyük önem arz etmektedir.

Sistemimizde, kan ve kan bileşenlerinin toplanması, test edilmesi, hazırlanması, depolanması ve dağıtımı konularında görev Bölge Kan Merkezlerine verilmiş fakat kan ve kan bileşeni ihtiyaçlarının öncelikle hastane transfüzyon merkezi stoklarından karşılanması öngörülmüştür. Kan ve kan bileşenlerine ihtiyaç duyulduğu anda ve hızlı bir şekilde ulaşabilmek transfüzyon merkezlerinde başarılı bir stok sisteminin kurulması ve bulundurulan stokların kritik seviyelerinin takibi ile mümkün olacaktır.

Kan ve Kan Ürünleri Yönetmeliğinin 9. Maddesi, 2. Fıkrası (f) bendi “Sorumluluk alanı içindeki transfüzyon merkezlerinin ihtiyaç duyduğu kan ve kan bileşenlerini sağlamak, protokolde belirtilen kritik stok seviyesini takip etmek, stoklanan kan miktarını kritik stok seviyesi altına düşürmemek için TM'nin talebini karşılamakla yükümlüdür.” hükmü gereğince transfüzyon merkezlerinin kritik stok seviyesinin tespiti ve korunması konusunda, bölge kan merkezlerine sorumluluk yüklemiş ve bu sorumluluğun transfüzyon merkezinin talebi doğrultusunda gerçekleşeceğini hüküm altına almıştır.

Transfüzyon merkezlerinin, kan ve kan bileşenlerine ihtiyaç halinde hızlı bir şekilde ulaşabilmesi için kan ve kan bileşeni stoklarını bağlı bulundukları bölge kan merkezi ile koordineli bir şekilde belirlemesi ve stokların kritik seviyenin altına düşürülmemesi yönünde hastane yönetimleri tarafından her türlü önlemin alınması hususunda;

Bilgilerinizi ve gereğini önemle rica ederim.

Prof. Dr. Nihat TOSUN
Bakan a.
Müsteşar

DAĞITIM:
Gereği:
Türkiye Kamu Hastaneleri Kurumuna
81 İl Valiliğine

Bilgi:
Türk Kızılayı Kan Hizmetleri Genel Müdürlüğüne
"""
with open(fpath10, 'w', encoding='utf-8') as f:
    f.write(content10.strip() + '\n')
print("Dosya 10 güncellendi.")

