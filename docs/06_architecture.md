# Mimari ve İş Akışı

BookLab, Django MVT yapısı üzerine kurulu özel bir laboratuvar randevu sistemidir. Son düzenlemelerle view, admin ve CSS katmanları daha okunabilir modüllere ayrılmıştır.

## Katmanlar

### Sunum Katmanı

- Django Template Language
- Bootstrap 5
- Bootstrap Icons
- FullCalendar
- Chart.js
- Merkezi CSS yapısı:
  - `static/css/booklab-base.css`
  - `static/css/booklab-corporate.css`
  - `static/css/pages/*.css`

### Backend Katmanı

- Django 5.2.11
- Session tabanlı kimlik doğrulama
- Form ve model validasyonları
- E-posta doğrulama ve şifre sıfırlama akışları
- PDF üretimi için xhtml2pdf / ReportLab

### Veri Katmanı

- Geliştirme ortamında SQLite
- Kullanıcı, profil, laboratuvar, cihaz, randevu, arıza ve duyuru modelleri
- Kullanıcı kaydı sonrası otomatik profil oluşturma için Django signal

## Güncel Modül Yapısı

### View Modülleri

`rezervasyon/views.py` artık yalnızca geriye dönük uyumluluk kapısıdır. Asıl view kodları konu bazlı ayrılmıştır:

- `views_auth.py`: giriş, kayıt, e-posta doğrulama, şifre sıfırlama
- `views_public.py`: ana sayfa ve laboratuvar detay
- `views_calendar.py`: genel/lab takvimleri ve event API'leri
- `views_randevu.py`: randevu alma, iptal, randevularım ve PDF
- `views_profile.py`: profil düzenleme ve e-posta değişikliği doğrulaması
- `views_management.py`: yönetim paneli, arıza, kullanıcı listesi ve toplu işlemler
- `view_helpers.py`: doğrulama kodu, kod süresi ve randevu çakışma yardımcıları

### Admin Modülleri

`rezervasyon/admin.py` yalnızca admin modüllerini yükler.

- `admin_helpers.py`: global admin aksiyonları, mail mixin'i ve güvenli redirect
- `admin_laboratuvar.py`: laboratuvar ve cihaz admin ekranları
- `admin_randevu.py`: randevu admin ekranı ve durum işlemleri
- `admin_kullanici.py`: kullanıcı, profil ve proxy kullanıcı adminleri
- `admin_ariza_duyuru.py`: arıza ve duyuru admin ekranları

## Temel İş Akışları

### Kullanıcı Kayıt Akışı

1. Kullanıcı kayıt formunu doldurur.
2. Sistem doğrulama kodu üretir ve e-posta gönderir.
3. Kod doğrulanırsa kullanıcı `is_active=False` olarak oluşturulur.
4. Profil `pasif_kullanici` statüsünde admin onayına düşer.
5. Admin onayı sonrası kullanıcı aktif olur ve sisteme giriş yapabilir.

### E-posta Değişikliği

1. Kullanıcı profil ekranında yeni e-posta adresini girer.
2. Sistem yeni adrese doğrulama kodu gönderir.
3. Kod doğrulanmadan eski e-posta korunur.
4. Kod doğruysa yeni e-posta hesaba uygulanır.

### Randevu Akışı

1. Kullanıcı laboratuvar ve cihaz seçer.
2. Tarih ve saat aralığı girer.
3. Sistem geçmiş tarih, süre ve cihaz çakışması kontrollerini yapar.
4. Uygun randevu `onay_bekleniyor` durumunda kaydedilir.
5. Yönetici randevuyu onaylar, reddeder veya yoklama durumuna çeker.

## Güvenlik Kararları

- Kritik durum değişiklikleri GET ile değil POST + CSRF ile yapılır.
- E-posta değişikliği doğrulama kodu olmadan uygulanmaz.
- Doğrulama kodları merkezi helper fonksiyonundan üretilir.
- Admin redirect işlemlerinde güvenli host kontrolü yapılır.

---

[Önceki: Veritabanı](05_database.md) | [Sonraki: Geliştirici Rehberi](07_dev_guide.md)
