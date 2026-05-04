<div align="center">

# BookLab-System

### Laboratuvar Rezervasyon ve Yönetim Sistemi

[![Python](https://img.shields.io/badge/Python-3.13.13-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2.11-green?style=for-the-badge&logo=django)](https://www.djangoproject.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey?style=for-the-badge&logo=sqlite)](https://www.sqlite.org/)

<img src="screenshots/BookLab_start.png" width="900" alt="BookLab Ana Ekran">

**BookLab**, üniversite laboratuvarlarında cihaz bazlı randevu, kullanıcı doğrulama, yönetici onayı, arıza bildirimi ve takvim takibi için geliştirilmiş Django tabanlı özel bir laboratuvar yönetim uygulamasıdır.

[Canlı Demo](https://booklabtr.duckdns.org/) | [Dokümantasyon](docs/README.md) | [Yerel Kurulum](docs/10_local_setup.md)

</div>

---

## Proje Özeti

BookLab, öğrencilerin ve yetkili personelin laboratuvar kaynaklarını kontrollü şekilde kullanmasını sağlar. Sistem özellikle cihaz bazlı randevu akışına, e-posta doğrulamasına, yönetici onayına ve randevu çakışma kontrolüne odaklanır.

Ana hedefler:

- Laboratuvar ve cihaz kullanımını tek merkezden yönetmek
- Kullanıcı kayıtlarını e-posta doğrulaması ve admin onayı ile güvenceye almak
- Cihaz bazlı randevu çakışmalarını engellemek
- Arıza, bakım ve pasif cihaz takibini kolaylaştırmak
- Öğrenci ve yönetici ekranlarını daha kurumsal, sade ve sürdürülebilir hale getirmek

---

## Öne Çıkan Özellikler

### Güvenlik ve Kullanıcı Akışı

- Kullanıcı kaydı sonrası 6 haneli e-posta doğrulama kodu
- E-posta doğrulansa bile admin onayı gelene kadar pasif hesap
- Profil e-posta değişikliğinde yeni adrese tekrar doğrulama kodu
- Şifre sıfırlama ve şifre değiştirme akışları
- Kritik işlemlerde POST ve CSRF koruması

### Randevu Yönetimi

- Laboratuvar ve cihaz bazlı randevu alma
- Aynı cihaz için saat aralığı çakışma kontrolü
- Onay bekliyor, onaylandı, geldi, gelmedi, reddedildi ve iptal durumları
- Kullanıcı randevu geçmişi ve PDF raporu
- Genel takvim ve laboratuvar bazlı takvim ekranları

### Yönetim Paneli

- Kullanıcı onay/pasif/aktif yönetimi
- Randevu onay, reddetme ve yoklama işlemleri
- Arızalı cihaz takibi ve cihazı pasife/aktife alma
- Duyuru yönetimi
- Toplu randevu işlemleri ve CSV dışa aktarma

---

## Güncel Teknik Yapı

Proje Django MVT mimarisi üzerinde çalışır. Son düzenlemelerle büyük dosyalar konu bazlı modüllere ayrılmıştır.

### Backend

- Python 3.13.13
- Django 5.2.11
- SQLite geliştirme veritabanı
- Django Jazzmin admin arayüzü
- WhiteNoise statik dosya servisi
- xhtml2pdf / ReportLab PDF üretimi

### Frontend

- Bootstrap 5
- Bootstrap Icons
- FullCalendar
- Chart.js
- Merkezi CSS yapısı:
  - `static/css/booklab-base.css`
  - `static/css/booklab-corporate.css`
  - `static/css/pages/*.css`

### Modüler Kod Yapısı

- `rezervasyon/views.py`: uyumluluk kapısı
- `rezervasyon/views_auth.py`: giriş, kayıt, doğrulama, şifre sıfırlama
- `rezervasyon/views_randevu.py`: randevu alma, iptal, PDF, randevularım
- `rezervasyon/views_management.py`: yönetim paneli ve toplu işlemler
- `rezervasyon/views_calendar.py`: takvim ve event API'leri
- `rezervasyon/views_profile.py`: profil ve e-posta değişikliği
- `rezervasyon/view_helpers.py`: ortak doğrulama ve çakışma yardımcıları
- `rezervasyon/admin.py`: admin modül yükleyici
- `rezervasyon/admin_*.py`: konu bazlı admin sınıfları
- `rezervasyon/admin_helpers.py`: admin aksiyonları ve yardımcıları

---

## Kurulum

Windows için önerilen kurulum Python 3.13.13 ile yapılmalıdır. MSYS Python kullanımı `cryptography` gibi paketlerde derleme sorunlarına yol açabilir.

```powershell
git clone https://github.com/resitasrav/BookLab-System.git
cd BookLab-System

$env:LOCALAPPDATA\Programs\Python\Python313\python.exe -m venv .venv
.\.venv\Scripts\activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Uygulama:

```text
http://127.0.0.1:8000/
```

Detaylı yerel kurulum notları için: [docs/10_local_setup.md](docs/10_local_setup.md)

---

## Ortam Değişkenleri

`.env.example` dosyasını `.env` olarak kopyalayıp kendi değerlerinle doldur:

```env
SECRET_KEY=change-me
DEBUG=True
EMAIL_HOST_USER=your-gmail@example.com
EMAIL_HOST_PASSWORD=your-google-app-password
DEFAULT_FROM_EMAIL=BookLab <your-gmail@example.com>
```

Eski `EMAIL_USER` ve `EMAIL_PASS` isimleri de geriye dönük uyumluluk için desteklenir.

---

## Doğrulama Komutları

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py runserver
```

Son doğrulama sonucu:

- `manage.py check`: başarılı
- `manage.py test`: 5 test başarılı
- `runserver`: `http://127.0.0.1:8000/` HTTP 200

---

## Dokümantasyon

- [Dokümantasyon Merkezi](docs/README.md)
- [Başlangıç Kılavuzu](docs/01_getting_started.md)
- [Kullanıcı Kılavuzu](docs/02_user_guide.md)
- [Yönetici Rehberi](docs/03_admin_guide.md)
- [API ve Backend](docs/04_api_docs.md)
- [Mimari](docs/06_architecture.md)
- [Geliştirici Rehberi](docs/07_dev_guide.md)
- [Refactor Notları](docs/11_refactor_notes.md)

---

## Not

Bu proje özel laboratuvar randevu kurallarına göre şekillendirilmiştir. Bazı iş kuralları genel rezervasyon sistemlerinden farklı olabilir; bu kurallar bilinçli olarak korunmuştur.
