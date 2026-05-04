# Sık Sorulan Sorular

## E-posta doğrulama kodu gelmiyor, ne yapmalıyım?

Önce spam/gereksiz klasörünü kontrol edin. Sonra `.env` içindeki SMTP bilgilerini doğrulayın:

- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `DEFAULT_FROM_EMAIL`

Gmail kullanılıyorsa normal hesap şifresi değil, Google uygulama şifresi kullanılmalıdır.

## Kayıt oldum ama giriş yapamıyorum. Neden?

E-posta doğrulandıktan sonra hesap yine de admin onayı bekler. Admin hesabı aktif etmeden kullanıcı giriş yapamaz.

## E-posta adresimi değiştirdim ama hemen değişmedi. Neden?

Güvenlik nedeniyle yeni e-posta adresine doğrulama kodu gönderilir. Kod doğrulanmadan eski e-posta korunur.

## Randevu alamıyorum. Olası nedenler neler?

- Cihaz pasif veya bakımda olabilir.
- Seçilen saat geçmişte olabilir.
- Bitiş saati başlangıçtan önce olabilir.
- Aynı cihaz için seçilen saat aralığında aktif başka randevu olabilir.
- Hesabınız admin tarafından aktif edilmemiş olabilir.

## Admin paneline nasıl girerim?

```text
http://127.0.0.1:8000/admin/
```

Giriş için staff/superuser yetkisi gerekir.

## `cryptography` kurulum hatası neden oldu?

PATH üzerindeki `python`, MSYS Python 3.12'ye gidiyordu. Bu ortamda `cryptography` hazır wheel yerine derleme yoluna düştü. Python 3.13.13 python.org kurulumu ile sorun çözüldü.

## Projeyi nasıl çalıştırırım?

```powershell
.\.venv\Scripts\activate
python manage.py runserver
```

## Dokümantasyon dosyalarını nerede bulurum?

Ana dokümantasyon indeksi:

```text
docs/README.md
```

---

[Önceki: Geliştirici Rehberi](07_dev_guide.md) | [Sonraki: Changelog](09_changelog.md)
