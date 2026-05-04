# Geliştirici Rehberi

Bu rehber BookLab kod tabanında yeni geliştirme yaparken izlenecek düzeni açıklar.

## Çalışma Ortamı

```powershell
.\.venv\Scripts\activate
python manage.py check
python manage.py test
python manage.py runserver
```

Bu projede Windows için Python 3.13.13 önerilir.

## Kod Organizasyonu

### View Katmanı

Yeni view eklerken doğrudan `views.py` içine yazmayın. Konuya göre ilgili dosyayı kullanın:

- Kimlik ve kayıt: `views_auth.py`
- Randevu: `views_randevu.py`
- Profil: `views_profile.py`
- Takvim/API: `views_calendar.py`
- Yönetim: `views_management.py`
- Ortak yardımcılar: `view_helpers.py`

Yeni view dışarıdan `rezervasyon.views` üzerinden kullanılacaksa `views.py` uyumluluk kapısına import ekleyin.

### Admin Katmanı

Yeni admin sınıfını konuya göre ilgili dosyaya ekleyin:

- Laboratuvar/cihaz: `admin_laboratuvar.py`
- Randevu: `admin_randevu.py`
- Kullanıcı/profil: `admin_kullanici.py`
- Arıza/duyuru: `admin_ariza_duyuru.py`
- Ortak aksiyon/mixin: `admin_helpers.py`

`admin.py` sadece modülleri yüklemek için kalmalıdır.

### CSS Katmanı

- Genel layout: `static/css/booklab-base.css`
- Kurumsal tema: `static/css/booklab-corporate.css`
- Sayfa bazlı stil: `static/css/pages/<sayfa>.css`

Template içine yeni `<style>` bloğu eklemeyin. Sayfaya özel CSS gerekiyorsa `extra_css` bloğu üzerinden yeni CSS dosyasını bağlayın.

## Türkçe Arama Başlıkları

Kodda hızlı arama için `TURKCE ARAMA` yorumları kullanılmıştır. Örnek:

```text
TURKCE ARAMA: randevu alma
TURKCE ARAMA: admin aksiyonlari
TURKCE ARAMA: profil duzenle
```

Yeni büyük bölüm eklerken benzer bir başlık bırakın.

## Güvenlik Kuralları

- Durum değiştiren işlemler GET ile yapılmamalıdır.
- Kritik işlemlerde POST + CSRF kullanılmalıdır.
- E-posta değişikliği doğrulama kodu olmadan uygulanmamalıdır.
- Randevu çakışma kontrolü model/view mantığı ile uyumlu kalmalıdır.

## Test

En azından şu alanlar test edilmelidir:

- Randevu çakışması
- Randevu iptali
- Admin durum güncellemesi
- Kayıt ve e-posta doğrulama
- Cihaz pasif/aktif akışı

Mevcut hızlı kontrol:

```powershell
python manage.py test
```

---

[Önceki: Mimari](06_architecture.md) | [Sonraki: SSS](08_faq.md)
