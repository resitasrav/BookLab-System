# Başlangıç Kılavuzu

## Sistem Gereksinimleri
- Python 3.13+
- Django 5.1+
- SQLite veya başka ilişkisel veritabanı
- Git

## Kurulum

```bash
git clone https://github.com/resitasrav/BookLab-System.git
cd BookLab-System
python -m venv venv
# Linux / MacOS
source venv/bin/activate
# Windows
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
# Tarayıcıyı açın : http://127.0.0.1:8000/