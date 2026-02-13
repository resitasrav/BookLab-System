# Geliştirici Rehberi

## Kod Standartları
- Python kodları PEP8 standartlarına uygun olmalı.
- Django model ve view naming konvansiyonlarına uyun.

## Branch ve Commit Stratejisi
- `main` → Kararlı sürümler
- `develop` → Aktif geliştirme
- Feature branch: `feature/<özellik_adı>`

## Yeni Özellik Ekleme
1. Feature branch oluştur
2. Gerekli model, view, template ve migration ekle
3. Testleri çalıştır ve doğrula
4. PR oluştur ve review sonrası merge

## Öneriler
- Kodun modüler ve yeniden kullanılabilir olmasına dikkat edin.
- Admin panelinde yeni alan eklerken migration dosyasını unutmayın.
