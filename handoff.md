# Handoff — Canlı Sağlık Mevzuatı

Son güncelleme: 2026-11-05 (Codex). Her oturum başında bu dosyayı oku; her büyük işlemden sonra güncelle.

## Hedef
mevzuat.gov.tr benzeri sağlık mevzuatı sitesi: kanun, CBK, KHK, tüzük, yönetmelik, yönerge, genelge, tebliğ, protokol ve Sağlık Bakanlığı yazışmaları; her tam metin için Word ve PDF indirme.

- Depo: https://github.com/rereprep/canli-saglik-mevzuati (herkese açık)
- Site: https://rereprep.github.io/canli-saglik-mevzuati/ (GitHub Pages, .github/workflows/yayinla.yml her push'ta derler)
- Yerel kopya: /Users/mithattemizer/Documents/Canlı Sağlık Mevzuatı/canli-saglik-mevzuati
- Gönderim: deploy key /tmp/csm-key/id_ed25519 (yalnızca bu depo, yazma yetkili; /tmp temizlenirse yeni anahtar üretip depo Settings > Deploy keys'e eklemek gerekir)
  `GIT_SSH_COMMAND="ssh -i /tmp/csm-key/id_ed25519 -o IdentitiesOnly=yes" git push origin main`
- Python: /Users/mithattemizer/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 (her zaman -I ile çalıştır; /tmp'deki .py dosyaları modülleri bozabiliyor)

## Kullanıcı kararları
- Ajanlar veya arka plan işleri çalışırken turu KAPATMA (son yanıt verme); kapatınca işler yarım kalıyor. Her şey bitene kadar izlemeye devam et, ara durumu kısa notlarla bildir.
- WorkBuddy (mcp__workbuddy__run_workbuddy_task) modelleri hy3 ve hy4free çalışıyor (2026-11-05): 3 işçi hy3, 3 işçi hy4free; biri hata verirse diğerine geç, ikisi de olmazsa Gemini Flash / luna alt ajanlarına dön.
- Siteyi düzenleyen: Mithat Temizer — yalnızca Hakkında sayfasında ve README'de.
- İthaf her sayfanın alt bilgisinde: "Her zaman ufkumu açan Prof. Dr. Cemil Özcan'a en derin saygılarımla."
- Ajanlar: Gemini 3.8 Flash (google-antigravity/gemini-3.8-flash) ve gpt-6-luna. Her zaman 6 ajan çalıştır. Kotaya (429) takılan ajanın kalan işini hemen diğer modelle yeni ajana ver (luna → Gemini Flash, Gemini Flash → luna). Bağlantı (502/ENOTFOUND) hatasında aynı modelle yeniden başlat. Biten/hata veren ajanı kapat ki sınır dolmasın.
- Kullanıcı: duran ajanın yerine önce "hy3" denenecek; spawn_agent hy3'ü tanımıyor (2026-11-05: "Unknown model hy3"), bu yüzden yukarıdaki eski usul geçerli. Yönetici döngüsü her yeni ajanda önce hy3'ü dener.
- Gönderim anahtarı kalıcı: /Users/mithattemizer/Documents/Canlı Sağlık Mevzuatı/.anahtar/id_ed25519 (git config core.sshCommand ayarlı; düz `git push origin main` yeterli).

## Kaynaklar ve işleme hattı
1. Kitaplar (kaynak klasörde, depoya girmez): mevzuat-kitabi.pdf (halk sağlığı, basılı s.+6=PDF), sbyonergevegenelge202520022025pdf.pdf (SB Yönergeler ve Genelgeler Kitabı 2025, basılı s.+14=PDF). Segmentler: kaynak-isleme/segmentler/*.json → araclar/kitaptan_cikar.py
2. Taranmış sayfalar: araclar/ocr_toplu.py (macOS Vision, ocr_vision.js; osascript için izin gerekir) → kaynak-isleme/ocr/
3. saglik.gov.tr: araclar/saglik_gov_tara.py (+ --ekleri-izle) → kaynak-isleme/indirilen (gitignore) → araclar/saglik_gov_aktar.py → segmentler/saglik-gov.json + katalog/saglik-gov.json
4. Word yönergeler: araclar/docx_aktar.py (Yönergeler klasörü)
5. Kataloglar (yalnızca künye): katalog.json (ajan), ozcan-halk-sagligi-ekleri.json (araclar/ozcan_ekleri.py, Özcan Halk Sağlığı 2. baskı Ek I–VII), saglik-gov.json, resmi-gazete-takip.json
6. Site: araclar/site_uret.py (--hizli: Word/PDF üretmez). Aynı belgenin kopyaları birleştirilir; eski adresler yönlendirilir.
   Birleştirme önceliği: Word kaynaklı > OCR'sız veya düzeltilmiş > daha uzun (eksiksiz) metin. Genelgeler sayı numarasıyla (ör. 2023/1) eşleşir.

## OCR düzeltme durumu
- OCR'lı belgeler künyede `ocr: true`; düzeltilenler `duzeltildi: true` (kitaptan_cikar bunları ezmez).
- Kalan düzeltilmemiş: `grep -l '^ocr: true' icerik/*/*.md | xargs grep -L '^duzeltildi: true'` — 2026-11-05 itibarıyla 0. Tüm OCR'lı belgeler ajanlarca kaynakla karşılaştırılıp düzeltildi (bazılarında okunamayan yerler [?] ile işaretli).
- Ajanlar künyeye bazen tırnaksız değer yazıyor: /tmp/csm-test/kunye_duzelt.py ile standartlaştır (yoksa yeniden yaz: değerleri json.dumps ile yaz, ocr/duzeltildi "true" → true).
- Etkili ajan talimatı: her turda listedeki düzeltilmemiş ilk 5 dosyayı düzelt ve kaydet; bitince yeniden görevlendir.

## Bilinen eksikler / sonraki adımlar
- ÖNEMLİ (2026-11-05): Bölüm başlığı yazılı olup gövdesi taranmış görüntü olan sayfalar (metin 80–600 karakter, büyük görüntü) OCR'dan kaçmıştı; bazı ajanlar bu kısımları UYDURMUŞTU (ör. 2025/6 Teftiş genelgesinde yanlış birim, sayı ve maddeler). 353 sayfa OCR'landı (ocr_toplu.py --sayfalar). Etkilenen 323 belgenin künyesinde `sayfa_kontrol` alanı var; ham OCR'ları kaynak-isleme/ocr-ek/<id>.txt. Ajanlar bu sayfaları görüntüyle karşılaştırıp düzeltiyor; bitince sayfa_kontrol silinip kontrol_edildi eklenir. kitaptan_cikar artık metni <600 karakter olan sayfalarda OCR varsa onu kullanıyor.
- Ajan talimatlarında "eksik kısmı tamamla" denirken mutlaka "yalnızca görüntüde gördüğünü yaz, tahmin etme" vurgulanmalı.
- 2026-11-05 akşam durumu:
  - Künye kayıtları tamamlanıyor: araclar/mevzuat_gov_aktar.py (güncel metin; kaynak-isleme/mevzuat-gov/eslesme.json) ve araclar/resmi_gazete_aktar.py (ilk yayımlanan metin; segmentler/resmi-gazete.json). Tam metin 661 → 967. mevzuat.gov.tr erişim kesintisinde aktarım ~221/325'te durdu; erişim gelince eslesme.json'daki boş kayıtları silip yeniden çalıştır.
  - saglik.gov.tr: tebliğ ve alt site sayfaları da izleniyor; sayfa içi genelge metinleri (pages_content) içeriğe alınıyor (saglik_gov_aktar.html_yaz).
  - Resmî Gazete takibinde Gemini kullanılmıyor (kullanıcı kararı); depo ayarında "Allow GitHub Actions to create and approve pull requests" açıldı.
  - OCR hızlı kontrolü sürüyor: künyede `kontrol_edildi: true` olanlar ikinci kez kontrol edildi (243/540; bu turda sonraki 5 genelge sayfası görüntüyle karşılaştırıldı). Kalan: `grep -l '^ocr: true' icerik/*/*.md | xargs grep -L '^kontrol_edildi: true'`.
- OCR düzeltmesi tamamlandı (2026-11-05). Yeni eklenen OCR'lı belgeler için aynı ajan akışını kullan.
- Ajan raporlarındaki notlar: bazı yönergelerde onay tarihi kaynakta boş ("…/…/2019"); bu künyeler bilerek boş bırakıldı. Birim adları künyede bugünkü adlarla, metinde eski adlarla geçebilir.
- Resmî Gazete takibi için depo Settings > Secrets'a GEMINI_API_KEY eklenebilir; otomatik PR için Actions > "Allow GitHub Actions to create pull requests" açılmalı.
- saglik.gov.tr'de 62 genelge kaydı alt liste sayfası (ör. devredilen birimlerin genelgeleri) olarak kaldı; ayrıca taranmadı.
- Künye tarih/sayı eksikleri için araclar/zenginlestirme_listesi.py + kaynak-isleme/zenginlestirme/*.json katmanı hazır, henüz kullanılmadı.

