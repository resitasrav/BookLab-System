# Başlangıç Kılavuzu

Bu rehber BookLab projesini temiz bir Python 3.13.13 ortamında çalıştırmak için hazırlanmıştır.

## Sistem Gereksinimleri

- Windows 10/11
- Python 3.13.13
- Git
- SQLite
- İnternet bağlantısı

Not: MSYS Python bu proje için önerilmez. `cryptography` gibi paketler MSYS ortamında kaynak koddan derlenmeye çalışıp hata verebilir.

## Kurulum

```powershell
git clone https://github.com/resitasrav/BookLab-System.git
cd BookLab-System

$env:LOCALAPPDATA\Programs\Python\Python313\python.exe -m venv .venv
.\.venv\Scripts\activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Ortam Dosyası

`.env.example` dosyasını `.env` olarak kopyalayın ve SMTP bilgilerini girin.

```powershell
copy .env.example .env
```

Gerekli temel alanlar:

```env
SECRET_KEY=change-me
DEBUG=True
EMAIL_HOST_USER=your-gmail@example.com
EMAIL_HOST_PASSWORD=your-google-app-password
DEFAULT_FROM_EMAIL=BookLab <your-gmail@example.com>
```

## Veritabanı

```powershell
python manage.py migrate
python manage.py createsuperuser
```

## Çalıştırma

```powershell
python manage.py runserver
```

Tarayıcı:

```text
http://127.0.0.1:8000/
```

## Kontrol Komutları

```powershell
python manage.py check
python manage.py test
```

Son bilinen durum:

- `check`: başarılı
- `test`: 5 test başarılı
- `runserver`: HTTP 200

Detaylı ortam notları: [10_local_setup.md](10_local_setup.md)

---

[Sonraki: Kullanıcı Kılavuzu](02_user_guide.md)
