# Segment ve katalog şeması

Ajanlar yalnızca JSON üretir; Markdown metinleri `araclar/kitaptan_cikar.py` oluşturur.

## Segment dosyası (`kaynak-isleme/segmentler/<kitap>.json`)

Bir JSON dizisi. Her öğe kitaptaki tek bir belgedir. Alanlar:

- id: benzersiz, ascii, küçük harf, tire ile (ör. "aile-hekimligi-kanunu")
- baslik: resmi ad, düzgün Türkçe yazım (ör. "Aile Hekimliği Kanunu")
- tur: aşağıdaki türlerden biri
- kaynak_pdf: "mevzuat-kitabi.pdf" veya "sbyonergevegenelge202520022025pdf.pdf"
- pdf_baslangic, pdf_bitis: 1 tabanlı PDF sayfa numarası (basılı sayfa değil), bitiş dahil
- baslik_satiri (isteğe bağlı): başlangıç sayfasında belgenin başladığı satırın metni (aynı sayfada önceki belge bitiyorsa)
- sonraki_baslik_satiri (isteğe bağlı): bitiş sayfasında sonraki belgenin başladığı satırın metni (bu satır ve sonrası kesilir)
- tarih: kabul/onay/imza tarihi, ISO (YYYY-MM-DD); bilinmiyorsa ""
- sayi: kanun no / genelge no (ör. "2021/5") / yazı sayısı; yoksa ""
- rg_tarih, rg_sayi: Resmî Gazete tarihi (ISO) ve sayısı; yoksa ""
- birim: yayımlayan birim (ör. "Halk Sağlığı Genel Müdürlüğü"); yoksa ""
- konu: tek cümlelik konu özeti
- etiketler: 2-5 küçük harfli konu etiketi dizisi
- kaynak: kitap adı ve basılı sayfa aralığı (ör. "Halk Sağlığı Hizmetleri Mevzuat Kitabı (2025), s. 24-28")
- not (isteğe bağlı): ör. "Kitapta yalnızca Sağlık Bakanlığı ile ilgili maddeler yer alıyor"

## Türler

kanun, cbk (Cumhurbaşkanlığı kararnamesi), khk, tuzuk, yonetmelik, yonerge, genelge, teblig, protokol, yazi (resmî yazı, talimat, duyuru, form, rehber ve benzeri önemli yazışmalar).

## Katalog dosyası (`kaynak-isleme/katalog/<ad>.json`)

Tam metni kitaplarda bulunmayan, resmi kaynağa bağlantı verilecek mevzuat. Segment alanlarının aynısı; sayfa alanları yerine kaynak_url (mevzuat.gov.tr, saglik.gov.tr, resmigazete.gov.tr vb. resmi bağlantı) ve isteğe bağlı degisiklikler (dizi: {"rg_tarih","rg_sayi","aciklama"}) bulunur.

