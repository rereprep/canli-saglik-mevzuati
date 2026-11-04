import os, re

# ==================== DOSYA 11 ====================
fpath11 = "/Users/mithattemizer/Documents/Canlı Sağlık Mevzuatı/canli-saglik-mevzuati/icerik/genelge/sb-kronik-yara-bakim-hizmetleri-genelgesi-2022-8.md"
with open(fpath11, 'r', encoding='utf-8') as f:
    text11 = f.read()

parts11 = text11.split('---', 2)
body11 = parts11[2].strip()

fm11 = """---
id: "sb-kronik-yara-bakim-hizmetleri-genelgesi-2022-8"
baslik: "Kronik Yara Bakım Hizmetleri Genelgesi (2022/8)"
tur: "genelge"
sayi: "2022/8"
tarih: "2022-12-06"
birim: "Sağlık Hizmetleri Genel Müdürlüğü"
konu: "Kronik yara bakım birimleri ve merkezlerinin fiziki standartları, çalışma esasları ve sevk zincirini düzenler."
etiketler: ["yara bakımı", "kronik yara", "sağlık tesisleri"]
kaynak: "Sağlık Bakanlığı Yönergeler ve Genelgeler Kitabı (2025), s. 181-184"
durum: "yürürlükte"
ocr: true
duzeltildi: true
---"""

header_page181 = """2.3.19. Kronik Yara Bakım Hizmetleri Genelgesi (2022/8)

### T.C. SAĞLIK BAKANLIĞI
Sağlık Hizmetleri Genel Müdürlüğü

Sayı : 54567092-
Konu : Kronik Yara Bakım Hizmetleri

GENELGE
2022/8

Tedavileri zor ve uzun süren, multidisipliner bir çalışmayı gerektiren kronik yaralar gerek hastalarda oluşturdukları olumsuz etkiler, gerekse sağlık çalışanları ve sağlık sistemine getirdiği külfet açısından tüm gelişmiş ve gelişmekte olan toplumlar için büyük bir sorun olup başvuran hastaların teşhis ve tedavi sürecini gerçekleştirmek, oluşabilecek komplikasyonları önlemek/azaltmak, kronik yara bakımı verecek sağlık tesislerinde klinikler arasında koordinasyonu sağlamak amacıyla; kronik yara hizmetleri ile ilgili iş ve işlemlerin düzenlenmesi ihtiyacı doğmuştur.

Bu maksatla ülkemizde sunulacak kronik yara bakım hizmetlerine ilişkin usul ve esasları düzenleyen 6/7/2021 tarihli ve (2021/04) sayılı Kronik Yara Bakım Hizmetleri Genelgesi yayımlanmış ve yürürlüğe girmiştir. Ancak Kronik Yara Bakım Hizmetleri Genelgesinin (2021/4) yayımlandığı tarihten bu yana Bakanlığımızca yapılan değerlendirmeler sonucunda bazı değişikliklerin yapılmasına ihtiyaç duyulmuş olup, bahsi geçen genelge yürürlükten kaldırılmıştır. Bu kapsamda, ülkemizde sunulacak kronik yara bakım hizmetlerine ilişkin usul ve esaslar ekte belirtilen şekliyle yeniden düzenlenmiştir. Genelgenin ilinizde bulunan kamu ve özel tüm sağlık tesislerine duyurulması, kronik yara tanısı, tedavisi ve takibi için sunulan sağlık hizmetlerinin işbu Genelge kapsamında yürütülmesi hususunda;

Bilgilerinizi ve gereğini önemle arz/rica ederim.

Prof. Dr. Sabahattin AYDIN
Bakan a.
Bakan Yardımcısı

Ek: Kronik Yara Bakım Hizmetlerine İlişkin Usul ve Esaslar (8 sayfa)

Dağıtım:
Gereği:
81 İl Valiliği (İl Sağlık Müdürlüğü)

Bilgi:
Cumhurbaşkanlığı
TBMM Başkanlığı
Sosyal Güvenlik Kurumu
Yükseköğretim Kurulu Başkanlığı
A Planı
"""

if "Tedavileri zor ve uzun süren" not in body11:
    idx_usul = body11.find("### KRONİK YARA BAKIM HİZMETLERİNE İLİŞKİN USUL VE ESASLAR")
    if idx_usul != -1:
        body11 = header_page181 + "\n" + body11[idx_usul:]

body11 = re.sub(r'T.C.s+SAĞLIKs+BAKANLIĞIs+YÖNERGELERs+VEs+GENELGELERs+KİTABI', '', body11, flags=re.IGNORECASE)
body11 = re.sub(r'^s*d+s*$', '', body11, flags=re.MULTILINE)

fixes11 = [
    ("Sağlık Bakamını", "Sağlık Bakanını"),
    ("Sağlık Bakanlığımı", "Sağlık Bakanlığını"),
    ("öyküsül", "öyküsü"),
    ("tarafindan", "tarafından"),
    ("ayrıntıhı", "ayrıntılı")
]
for src, dst in fixes11:
    body11 = body11.replace(src, dst)

body11 = re.sub(r'\n{3,}', '\n\n', body11)
with open(fpath11, 'w', encoding='utf-8') as f:
    f.write(fm11 + "\n\n" + body11 + "\n")
print("Dosya 11 güncellendi.")

# ==================== DOSYA 12 ====================
fpath12 = "/Users/mithattemizer/Documents/Canlı Sağlık Mevzuatı/canli-saglik-mevzuati/icerik/genelge/sb-kuduzla-mucadele-ve-profilaksi-uygulamalari-genelgesi-2019-04.md"
with open(fpath12, 'r', encoding='utf-8') as f:
    text12 = f.read()

parts12 = text12.split('---', 2)
body12 = parts12[2].strip()

fm12 = """---
id: "sb-kuduzla-mucadele-ve-profilaksi-uygulamalari-genelgesi-2019-04"
baslik: "Kuduzla Mücadele ve Profilaksi Uygulamaları Genelgesi (2019/04)"
tur: "genelge"
sayi: "2019/04"
tarih: "2019-05-11"
birim: "Halk Sağlığı Genel Müdürlüğü"
konu: "Kuduz riskli temas vakalarında profilaksi uygulamaları, aşı merkezleri ve sürveyans bildirim esaslarını düzenler."
etiketler: ["kuduz", "profilaksi", "zoonoz", "aşı"]
kaynak: "Sağlık Bakanlığı Yönergeler ve Genelgeler Kitabı (2025), s. 646-648"
durum: "yürürlükte"
ocr: true
duzeltildi: true
---"""

body12 = re.sub(r'T.C.s+SAĞLIKs+BAKANLIĞIs+YÖNERGELERs+VEs+GENELGELERs+KİTABI', '', body12, flags=re.IGNORECASE)
body12 = re.sub(r'^s*d+s*$', '', body12, flags=re.MULTILINE)
body12 = re.sub(r'LALKs+SAỘL.*?D,AZRANTA', '', body12)
body12 = re.sub(r'11/5/2019s+1414', '', body12)

fixes12 = [
    ("Halk: Sallgi Gencl Müdurlüga", "Halk Sağlığı Genel Müdürlüğü"),
    ("Say) 1 10712557-136.99", "Sayı : 10712557-136.99"),
    ("Kono : Kuduzia Múcadele ve\n\nProfilakei Dygglatalani", "Konu : Kuduzla Mücadele ve Profilaksi Uygulamaları"),
    ("GENELGE 2019/0.4", "GENELGE 2019/04"),
    ("musan sağlığıur", "insan sağlığını"),
    ("kimik belirtiler", "klinik belirtiler"),
    ("mümkan aimayan", "mümkün olmayan"),
    ("zooroek", "zoonotik"),
    ("Be sebeple", "Bu sebeple"),
    ("nakli temas", "riskli temas"),
    ("knouz riskb", "kuduz riskli"),
    ("gerçekleştırılmes", "gerçekleştirilmesi"),
    ("änemlidiz", "önemlidir."),
    ("Køduz hastalığıölöncil bichasabk olması nereniye", "Kuduz hastalığı ölümcül bir hastalık olması nedeniyle"),
    ("tisklı tenıstılarda aşılamanım", "riskli temaslılarda aşılamanın"),
    ("konuşunda", "konusunda"),
    ("bagilendin mesı elzemdir", "bilgilendirilmesi elzemdir."),
    ("kuduz tisklı", "kuduz riskli"),
    ("Prof. Dr. Emin ALP MESE\n\nBakan a\n\nBakin Yardınes", "Prof. Dr. Emine ALP MEŞE\nBakan a.\nBakan Yardımcısı"),
    ("Kuluz Profilalesi", "Kuduz Profilaksi"),
    ("Kuche Aşi Takip Karsı", "Kuduz Aşı Takip Kartı"),
    ("4. Kuduz Riskl Temas Vaka Inceleme Formn", "4- Kuduz Riskli Temas Vaka İnceleme Formu"),
    ("4- Buduz Riskli Temas Aylik Islen Farmw", "5- Kuduz Riskli Temas Aylık İcmal Formu"),
    ("Dogune Gereği: A Plan", "DAĞITIM:\nGereği: A Planı")
]
for src, dst in fixes12:
    body12 = body12.replace(src, dst)

body12 = re.sub(r'\n{3,}', '\n\n', body12)
with open(fpath12, 'w', encoding='utf-8') as f:
    f.write(fm12 + "\n\n" + body12 + "\n")
print("Dosya 12 güncellendi.")

# ==================== DOSYA 13 ====================
fpath13 = "/Users/mithattemizer/Documents/Canlı Sağlık Mevzuatı/canli-saglik-mevzuati/icerik/genelge/sb-kurumlarimizda-yer-alan-ticari-alanlarin-kiraya-verilmesi-genelgesi-2011-43.md"
with open(fpath13, 'r', encoding='utf-8') as f:
    text13 = f.read()

parts13 = text13.split('---', 2)
body13 = parts13[2].strip()

fm13 = """---
id: "sb-kurumlarimizda-yer-alan-ticari-alanlarin-kiraya-verilmesi-genelgesi-2011-43"
baslik: "Kurumlarımızda Yer Alan Ticari Alanların Kiraya Verilmesi Genelgesi (2011/43)"
tur: "genelge"
sayi: "2011/43"
birim: "Strateji Geliştirme Başkanlığı"
konu: "Sağlık tesislerinde bulunan kantin, kafeterya ve ticari alanların kiraya verilmesi ve denetimini düzenler."
etiketler: ["ticari alanlar", "kiralama", "döner sermaye", "kantin"]
kaynak: "Sağlık Bakanlığı Yönergeler ve Genelgeler Kitabı (2025), s. 504-507"
durum: "yürürlükte"
ocr: true
duzeltildi: true
---"""

header_page504 = """6.3.10. Kurumlarımızda Yer Alan Ticari Alanların Kiraya Verilmesi Genelgesi (2011/43)

### T.C. SAĞLIK BAKANLIĞI
Strateji Geliştirme Başkanlığı

Sayı : B.10.0.SGB.0.84.00.01/10-06-
Konu : Kurumlarımızda yer alan ticari alanların kiraya verilmesi.

............ VALİLİĞİNE
(İl Sağlık Müdürlüğü)

GENELGE
2011/43

Bilindiği üzere 6225 sayılı “Bazı Kanun ve Kanun Hükmünde Kararnamelerde Değişiklik Yapılmasına Dair Kanun”un 2 inci maddesi ile 4/1/1961 tarihli ve 209 sayılı Sağlık Bakanlığına Bağlı Sağlık Kurumları ile Esenlendirme (Rehabilitasyon) Tesislerine Verilecek Döner Sermaye Hakkında Kanunun 3 üncü maddesinin birinci fıkrasına (h) bendinden sonra gelmek üzere (ı) ve (i) bentleri eklenmiştir.

209 sayılı Kanuna eklenen (ı) bendinde; “Bakanlık sağlık kurum ve kuruluşlarının 31/12/1960 tarihli ve 193 sayılı Gelir Vergisi Kanununun 70 inci maddesinde belirtilen mal ve hakların kiralanması...” hükmüne yer verilerek mal ve hakların kiralanmasından elde edilecek gelirlerin işletme döner sermayesine gelir kaydedebilmesinin yolu açılmıştır.

Bu amaçla, Mülkiyeti Hazineye ait /Hazine ile hisseli/ üst yapı Hazineye ait ya da zemini Hazineye ait olup, Sağlık Bakanlığına tahsisli olan yerler ile Sağlık Bakanlığınca kiralanmış ve kira bedelleri merkezi yönetim bütçesinden karşılanan hastane ve birinci basamak sağlık kurumlarındaki ticari amaçla kullanılması mümkün olan bölümlerinin (söz konusu taşınmazların Aile Hekimlerine kiralanması dahil olmak üzere) Sağlık Bakanlığı tarafından Döner Sermaye İşletmeleri eliyle işlettirilmesine ilişkin esas ve usullerin belirlenmesi amacıyla Maliye Bakanlığı ile Bakanlığımız arasında 15/06/2011 tarihinde protokol imzalanmıştır.

Protokol, mevcut ticari alanlar ile protokolün imzalanmasından sonra Sağlık Bakanlığınca oluşturulacak yeni ticari alanları kapsamaktadır.

Kurumlarımız arasında uygulama birliğinin sağlanması amacıyla protokol hükümlerinin üçüncü kişileri de ilgilendirilen hükümleri ve diğer hususlar aşağıda belirtilmiştir.

A. Protokol Hükümleri

1. Protokolün süresi, protokolün imzalandığı tarihten itibaren 10 (On) yıl olup, Bakanlığımıza bağlı kurumlar ile üçüncü kişiler arasında düzenlenecek sözleşmeler hiçbir şekilde protokol süresini aşmayacaktır.
2. Üçüncü kişiler ile yapılacak sözleşmelere, protokolün herhangi bir gerekçe ile sona ermesi halinde kira sözleşmesinin de sona ereceğine ve bu şekilde sona ermeden dolayı herhangi bir hak ve tazminat talebinde bulunulmayacağına dair hüküm konulacaktır.
3. Üçüncü kişilere hiçbir şekilde kiralama karşılığında ticari alan yaptırılmayacaktır.
4. Bakanlığımıza bağlı kurumlardaki ticari alanlar hiçbir şekilde bedelsiz olarak işlettirilmeyecektir.
5. Bakanlığımıza bağlı kurumlar ile üçüncü kişiler arasında düzenlenen sözleşmenin (Mülkiyeti üçüncü şahıslara ait olmakla birlikte kullanım hakkı Bakanlığımıza veya Valiliğe bırakılan taşınmazlardaki ticari alanlar ile döner sermaye kaynaklarından kiralanan taşınmazlardaki ticari alanların kiraya verilmesi sonucunda düzenlenen sözleşmeler ve Aile Hekimleri ile yapılan sözleşmeler hariç) bir örneği sözleşmenin düzenlenmesinden itibaren 1 (Bir) ay içinde ilgili Defterdarlığa gönderilecektir.
"""

if "Bilindiği üzere 6225 sayılı" not in body13:
    idx_m6 = body13.find("6. Bünyesinde ticari alan bulunan")
    if idx_m6 != -1:
        body13 = header_page504 + "\n" + body13[idx_m6:]

body13 = re.sub(r'T.C.s+SAĞLIKs+BAKANLIĞIs+YÖNERGELERs+VEs+GENELGELERs+KİTABI', '', body13, flags=re.IGNORECASE)
body13 = re.sub(r'^s*d+s*$', '', body13, flags=re.MULTILINE)

fixes13 = [
    ("bağhı", "bağlı"),
    ("kapaulması", "kapatılması"),
    ("Il Sağhk", "İl Sağlık"),
    ("taşınmazlerın", "taşınmazların"),
    ("B. Mevcut Süzleşmeler", "B. Mevcut Sözleşmeler"),
    ("protokollin", "protokolün"),
    ("aymı", "aynı"),
    ("Meveut", "Mevcut"),
    ("kiracıfara", "kiracılara"),
    ("devredıldığı", "devredildiği"),
    ("Maderiağünün", "Müdürlüğünün"),
    ("dasyalarıın", "dosyalarının"),
    ("ürneğı", "örneği"),
    ("şcklinde", "şeklinde"),
    ("Profe: Dr. Nihat TOSUN", "Prof. Dr. Nihat TOSUN")
]
for src, dst in fixes13:
    body13 = body13.replace(src, dst)

body13 = re.sub(r'\n{3,}', '\n\n', body13)
with open(fpath13, 'w', encoding='utf-8') as f:
    f.write(fm13 + "\n\n" + body13 + "\n")
print("Dosya 13 güncellendi.")

# ==================== DOSYA 14 ====================
fpath14 = "/Users/mithattemizer/Documents/Canlı Sağlık Mevzuatı/canli-saglik-mevzuati/icerik/genelge/sb-kutanoz-leishmaniasis-genelgesi-2003-126.md"
with open(fpath14, 'r', encoding='utf-8') as f:
    text14 = f.read()

parts14 = text14.split('---', 2)
body14 = parts14[2].strip()

fm14 = """---
id: "sb-kutanoz-leishmaniasis-genelgesi-2003-126"
baslik: "Kutanöz Leishmaniasis Genelgesi (2003/126)"
tur: "genelge"
sayi: "2003/126"
tarih: "2003-10-24"
birim: "Temel Sağlık Hizmetleri Genel Müdürlüğü"
konu: "Kutanöz Leishmaniasis (şark çıbanı) olgularında tanı, tedavi yaklaşımı ve kontrol programı ilkelerini düzenler."
etiketler: ["leishmaniasis", "şark çıbanı", "paraziter hastalıklar", "bulaşıcı hastalıklar"]
kaynak: "Sağlık Bakanlığı Yönergeler ve Genelgeler Kitabı (2025), s. 613-616"
durum: "yürürlükte"
ocr: true
duzeltildi: true
---"""

header_page613 = """6.3.19. Kutanöz Leishmaniasis Genelgesi (2003/126)

### T.C. SAĞLIK BAKANLIĞI
Temel Sağlık Hizmetleri Genel Müdürlüğü

SAYI : B100TSH0110002 / 16130
KONU : Kutanöz Leishmaniasis
24.10.2003

GENELGE
2003/126

İLGİ: 25.06.1996 tarihli ve B100TSH0110002/6078 sayılı Genelgemiz.

Bilindiği gibi Leishmaniasis, Leishmania cinsi parazitler ile enfekte dişi kum sineklerinin (Tatarcık, Phlebotomus) kan emmesi sırasında insanlara bulaştırdığı bir hastalıktır. İnsanlarda üç tip klinik tablo ile seyreden hastalığın Ülkemizde en çok görülen şekli Kutanöz Leishmaniasis (KL) olup, Şanlıurfa, Osmaniye, Adana, Hatay, Kahramanmaraş ve Mersin illerimizde endemik olarak görülmektedir.

Malûm olduğu üzere, KL ile ilgili tanı ve tedavi kriterleri ile vektör ve çevreye yönelik hizmetler ilgi genelgemiz ve ekinde gönderilen Kutanöz Leishmaniasis Kontrol Programı kapsamında verilen bilgiler çerçevesinde yürütülmektedir.

Ancak, ortaya çıkan bir takım gelişmeler ve bu gelişmeler neticesinde yapılan değerlendirmeler, ilgi genelgemiz çerçevesinde yürütülen hizmetlere ilişkin yeni bir mütalaanın gerekliliğini ortaya koymuştur.

Bu meyanda, yeniden değerlendirilen, KL olgularında tanı ve tedavide yaklaşım ilkeleri ekte gönderilmektedir.

Bu nedenle, KL ile ilgili hizmetlerin ilişikteki bilgiler çerçevesinden yürütülmesi ve ilgi genelgemizin iptal edildiği hususlarında bilgilerinizi, keyfiyetin gereği için de ilgililere emirlerinizi rica ederim.

EK: Kutanöz Leishmaniasis Olgularında Tanı ve Tedavide Yaklaşım (3 sf.)

Prof. Dr. Recep AKDAĞ
Sağlık Bakanı

DAĞITIM:
A Plânı

DAİMİ GENELGE
"""

if "Bilindiği gibi Leishmaniasis" not in body14:
    idx_olgu = body14.find("### KUTANÖZ LEİSHMANİA SİS OLGULARINDA TANI VE TEDAVİDE YAKLAŞIM")
    if idx_olgu != -1:
        body14 = header_page613 + "\n" + body14[idx_olgu:]

body14 = re.sub(r'T.C.s+SAĞLIKs+BAKANLIĞIs+YÖNERGELERs+VEs+GENELGELERs+KİTABI', '', body14, flags=re.IGNORECASE)
body14 = re.sub(r'^s*d+s*$', '', body14, flags=re.MULTILINE)

fixes14 = [
    ("KUTANÖZ LEİSHMANİA SİS", "KUTANÖZ LEİSHMANİASİS"),
    ("duşünulen", "düşünülen"),
    ("ozelikler", "özellikler"),
    ("vucudun", "vücudun"),
    ("clan", "olan"),
    ("ıyıleşmeyen", "iyileşmeyen"),
    ("infekte", "enfekte"),
    ("ağrisız", "ağrısız"),
    ("papul, nodul, nodulo-ulseratif, plak, ulsere", "papül, nodül, nodülo-ülseratif, plak, ülsere"),
    ("Olserleşmiş", "Ülserleşmiş"),
    ("endurasyon gosteren", "endürasyon gösteren"),
    ("görüldüğu", "görüldüğü"),
    ("teorık ve pratik eğitimlerinin yapılmasi; ayrica, bu eğıtimlerin surekliliğinin", "teorik ve pratik eğitimlerinin yapılması; ayrıca, bu eğitimlerin sürekliliğinin sağlanması,"),
    ("güstermelerinin", "göstermelerinin")
]
for src, dst in fixes14:
    body14 = body14.replace(src, dst)

body14 = re.sub(r'\n{3,}', '\n\n', body14)
with open(fpath14, 'w', encoding='utf-8') as f:
    f.write(fm14 + "\n\n" + body14 + "\n")
print("Dosya 14 güncellendi.")

# ==================== DOSYA 15 ====================
fpath15 = "/Users/mithattemizer/Documents/Canlı Sağlık Mevzuatı/canli-saglik-mevzuati/icerik/genelge/sb-mal-bildirimleri-konulu-genelge-2018-20.md"
with open(fpath15, 'r', encoding='utf-8') as f:
    text15 = f.read()

parts15 = text15.split('---', 2)
body15 = parts15[2].strip()

fm15 = """---
id: "sb-mal-bildirimleri-konulu-genelge-2018-20"
baslik: "Mal Bildirimleri Konulu Genelge (2018/20)"
tur: "genelge"
sayi: "2018/20"
tarih: "2018-07-09"
birim: "Yönetim Hizmetleri Genel Müdürlüğü"
konu: "Sağlık Bakanlığı personelinin mal bildiriminde bulunma usul ve esasları, bildirim zamanları ve idari süreçlerini düzenler."
etiketler: ["mal bildirimi", "personel", "mevzuat"]
kaynak: "Sağlık Bakanlığı Yönergeler ve Genelgeler Kitabı (2025), s. 1005-1009"
durum: "yürürlükte"
ocr: true
duzeltildi: true
---"""

header_page1005 = """9.3.6. Mal Bildirimleri Konulu Genelge (2018/20)

### T.C. SAĞLIK BAKANLIĞI
Yönetim Hizmetleri Genel Müdürlüğü

Sayı : 82040698/
Tarih: 09.07.2018
Konu : Mal Bildirimleri

GENELGE
2018/20

Bilindiği üzere gerçeğe aykırı mal bildiriminde bulunan, haksız mal edinen veya haksız edinilen malı kaçıran veya gizleyenlere 3628 sayılı Kanunda belirtilen ceza hükümler, süresi içinde mal bildiriminde bulunmayanlara ise 657 sayılı Kanunun disiplin hükümleri uygulanmaktadır.
3628 sayılı Mal Bildiriminde Bulunulması, Rüşvet ve Yolsuzluklarla Mücadele Kanunu ile bu Kanunun uygulanmasına ilişkin usul ve esasları düzenleyen ve 10/08/1990 tarihli ve 90/748 sayılı Bakanlar Kurulu Kararı ile yürürlüğe konulan Mal Bildiriminde Bulunulması Hakkında Yönetmeliğin öngördüğü işlemlerin yerine getirilmesi, uygulamada yaşanan sıkıntıların giderilmesi ve personelin mağduriyetinin önlenmesi amacına yönelik hususlar aşağıda belirtilmiştir.

A) MAL BİLDİRİMİNDE BULUNULMASINDA UYULMASI GEREKEN USUL VE ESASLAR

1. Mal bildiriminde bulunacak kamu görevlileri
Bakanlığımız merkez ve taşra teşkilatında aylık, ücret ve ödenek almak suretiyle kamu hizmeti gören memurlar ve işçi niteliği taşımayan diğer kamu görevlilerinden;
a) 657 sayılı Kanunun 4 üncü maddesinin birinci fıkrasının (A) bendine göre istihdam edilen memurların,
b) 657 sayılı Kanunun 4 üncü maddesinin birinci fıkrasının (B) bendine göre istihdam edilen sözleşmeli personelin,
c) 4924 sayılı Kanuna tabi sözleşmeli personelin,
ç) 5258 sayılı Aile Hekimliği Kanunu kapsamında sözleşme ile görev yapan personelin,
d) 663 sayılı KHK'nin Ek-2 sayılı cetvelinde belirtilen pozisyonlarda sözleşmeli statüde görev yapan personelin,
mal bildiriminde bulunması gerekmektedir.

2. Mal Bildiriminin Konusu
Mal Bildiriminde Bulunulması Hakkında Yönetmeliğin 8 inci maddesi hükmü çerçevesinde 3628 sayılı Kanun kapsamına giren kamu görevlilerinin kendilerine, eşlerine ve velayetleri altındaki çocuklarına ait bulunan;
a) Taşınmaz malları (arsa ve yapı kooperatif hisseleri dahil),
b) Kendilerine aylık ödenenler, net aylık tutarının beş katından fazla; aylık ödenmeyenler ise genel idare hizmetleri sınıfında birinci derecenin birinci kademesindeki şube müdürüne ödenen net aylığın beş katından fazla değer ve tutarındaki;
1) Para ve para hükmündeki kıymetli kağıtları,
2) Hisse senedi ve tahvilleri,
3) Altın ve mücevheratı,
"""

if "Bilindiği üzere gerçeğe aykırı mal bildiriminde" not in body15:
    idx_m4 = body15.find("4) Her türlü kara, deniz ve hava taşıt")
    if idx_m4 != -1:
        body15 = header_page1005 + "\n" + body15[idx_m4:]

body15 = re.sub(r'T.C.s+SAĞLIKs+BAKANLIĞIs+YÖNERGELERs+VEs+GENELGELERs+KİTABI', '', body15, flags=re.IGNORECASE)
body15 = re.sub(r'^s*d+s*$', '', body15, flags=re.MULTILINE)
body15 = re.sub(r'TCs+Sogas+Quartg', '', body15)

fixes15 = [
    ("inşeat ve iş makinalan", "inşaat ve iş makineleri"),
    ("ziraat makinalan", "ziraat makineleri"),
    ("ev eşyalan", "ev eşyaları"),
    ("Alacaklari", "Alacakları"),
    ("Borçlan", "Borçları"),
    ("ayrı ayn", "ayrı ayrı"),
    ("olmast", "olması"),
    ("eși", "eşi"),
    ("Müstesar", "Müsteşar"),
    ("ри.", ""),
    ("A Plam", "A Planı")
]
for src, dst in fixes15:
    body15 = body15.replace(src, dst)

body15 = re.sub(r'\n{3,}', '\n\n', body15)
with open(fpath15, 'w', encoding='utf-8') as f:
    f.write(fm15 + "\n\n" + body15 + "\n")
print("Dosya 15 güncellendi.")

