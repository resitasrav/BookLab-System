# Yerel Calistirma Notlari

Bu projede eski `venv` Python 3.13 WindowsApps yoluna bagli olusturulmus. Makinedeki aktif `python` yolu degisirse `venv\Scripts\python.exe` acilmayabilir ve `python manage.py runserver` Django bulamayabilir.

Bu ortamda Python 3.13.13 python.org kurulum dosyasi ile kullanici dizinine kuruldu:

```powershell
$env:LOCALAPPDATA\Programs\Python\Python313\python.exe
```

Onerilen temiz kurulum:

```powershell
$env:LOCALAPPDATA\Programs\Python\Python313\python.exe -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Not: MSYS Python ile `.venv\bin` olusabiliyor ve `cryptography` kaynaktan derlenmeye calisip hata verebiliyor. Windows icin bu projede python.org Python 3.13 kullanin.

`.env.example` dosyasini `.env` olarak kopyalayip SMTP ve gizli anahtar bilgilerini kendi ortam degerlerinizle doldurun.
