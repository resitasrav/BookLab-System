# BookLab Dokümantasyon Merkezi

Bu klasör BookLab projesinin kurulum, kullanım, yönetim, mimari ve geliştirme notlarını içerir.

## Rehber Haritası

| Dosya | İçerik | Hedef Kitle |
| :--- | :--- | :--- |
| [01_getting_started.md](01_getting_started.md) | Python 3.13.13 ile yerel kurulum ve çalıştırma | Geliştirici |
| [02_user_guide.md](02_user_guide.md) | Kullanıcı kayıt, giriş, profil ve randevu işlemleri | Öğrenci / Kullanıcı |
| [03_admin_guide.md](03_admin_guide.md) | Yönetici paneli, onay, randevu ve cihaz yönetimi | Yönetici / Akademisyen |
| [04_api_docs.md](04_api_docs.md) | Mevcut backend endpointleri ve iş mantığı | Geliştirici |
| [05_database.md](05_database.md) | Model ve veritabanı ilişkileri | Geliştirici |
| [06_architecture.md](06_architecture.md) | Güncel modüler mimari ve iş akışları | Geliştirici / Mimar |
| [07_dev_guide.md](07_dev_guide.md) | Kod standartları, modül düzeni ve test komutları | Geliştirici |
| [08_faq.md](08_faq.md) | Sık karşılaşılan sorunlar | Herkes |
| [09_changelog.md](09_changelog.md) | Sürüm ve refactor notları | Herkes |
| [10_local_setup.md](10_local_setup.md) | Bu makinedeki Python 3.13.13 ortam notları | Geliştirici |
| [11_refactor_notes.md](11_refactor_notes.md) | View, admin ve CSS refactor raporu | Geliştirici |

## Güncel Durum

- Python 3.13.13 ve Django 5.2.11 kullanılmaktadır.
- Eski kırık `venv` kaldırılmış, proje `.venv` ile çalışacak hale getirilmiştir.
- `cryptography` kurulumu Python 3.13.13 ortamında başarıyla tamamlanmıştır.
- View, admin ve CSS yapısı modüler hale getirilmiştir.
- `manage.py check`, `manage.py test` ve kısa `runserver` testi başarıyla geçmiştir.

## Hızlı Çalıştırma

```powershell
.\.venv\Scripts\activate
python manage.py runserver
```

Ana README'ye dönmek için: [../README.md](../README.md)
