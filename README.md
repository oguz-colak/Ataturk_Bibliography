# MARCXML'den ISBD Uyumlu Bibliyografya (PDF)

Bu depo, MARCXML kayıtlarından (özellikle 020, 090, 100, 111, 245, 250, 260, 300, 490, 650) ISBD odaklı bibliyografya çıktısı üretmek için örnek bir komut ve araç içerir.

## 7000 kayıt için toplu üretim komutu

```bash
python3 scripts/marcxml_to_pdf.py \
  --input data/kayitlar.xml \
  --output-pdf output/ataturk_bibliyografya.pdf \
  --title "Atatürk Bibliyografyası" \
  --dedup-mode copy
```

> Not: PDF üretimi için `weasyprint` gerekir. Kurulu değilse script yine HTML üretir ve PDF aşamasında hata verir.

## ISBD için kullanılan alanlar

- **020**: ISBN (birden fazla ISBN desteklenir)
- **090**: Yer numarası / sınıflama bilgisi
- **100**: Kişi yazar başlığı
- **111**: Toplantı/konferans başlığı (100 yoksa ana girişte kullanılır)
- **245**: Başlık, alt başlık, sorumluluk bildirimi
- **250**: Baskı bildirimi
- **260**: Yayım yeri, yayınevi, tarih
- **300**: Fiziksel tanım
- **490**: Dizi bilgisi
- **650**: Konu başlıkları

## Karma kayıtlar için önerilen yol

7000 kayıtta farklı yayın türleri (çok yazarlı kitaplar, sempozyum/konferans bildirileri, farklı baskılar, çoklu ISBN, aynı eserin çoklu nüshaları) için pratik yaklaşım:

1. **Önce kopya düzeyinde tekilleştirme** (`--dedup-mode copy`):
   - Aynı başlık+yazar/yetkili giriş+yayınevi+yıl+baskı kombinasyonunu tek kayıt tutar.
   - Aynı eserin birden fazla nüshasını bibliyografyada şişirmeden önler.
2. **Baskıları ayrı tutma**:
   - `250` (baskı) anahtarın içinde olduğu için farklı baskılar korunur.
3. **Çoklu ISBN’leri tek kayıtta birleştirme**:
   - 020$a değerleri tek girdide `;` ile listelenir.
4. **Konferans/sempozyum kayıtları**:
   - 100 yoksa 111 ana giriş gibi kullanılır.
5. **İleri seviye tekilleştirme (opsiyonel)**:
   - Çalışma düzeyinde agresif tekilleştirme için `--dedup-mode work` kullanılabilir (başlık+yazar/yetkili giriş).

## Önerilen yayın akışı

1. MARCXML validasyon (bozuk kayıtları raporla)
2. `--dedup-mode copy` ile ana bibliyografya üret
3. PDF öncesi hızlı kalite kontrol (örnek 100 kayıt)
4. Nihai PDF üretimi
5. Gerekirse `--dedup-mode none` ile "tam envanter" sürümü de yayımla

