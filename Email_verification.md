# E-posta Doğrulama ve Kullanıcı Onay Akışı

BookLab'de kullanıcı erişimi iki aşamalıdır: önce e-posta doğrulanır, ardından yönetici hesabı aktif eder.

## Kayıt Akışı

1. Kullanıcı kayıt formunu doldurur.
2. Sistem 6 haneli doğrulama kodu üretir.
3. Kod kullanıcının e-posta adresine gönderilir.
4. Kullanıcı kodu doğrular.
5. Hesap `is_active=False` olarak oluşturulur.
6. Profil `pasif_kullanici` statüsünde admin onayına düşer.
7. Admin onay verirse kullanıcı `aktif_kullanici` statüsüne geçer ve giriş yapabilir.

## Profil E-posta Değişikliği

1. Kullanıcı profil ekranında yeni e-posta adresini girer.
2. Sistem yeni adrese doğrulama kodu gönderir.
3. Kod doğru girilmeden eski e-posta korunur.
4. Kod doğruysa yeni e-posta hesaba uygulanır.

## Statü Matrisi

| Aşama | Profil `status` | `email_dogrulandi` | `is_active` | Giriş |
| :--- | :--- | :---: | :---: | :---: |
| Kayıt formu tamamlandı, kod bekleniyor | Henüz kullanıcı oluşmaz | False | False | Hayır |
| E-posta doğrulandı, admin bekleniyor | `pasif_kullanici` | True | False | Hayır |
| Admin onayladı | `aktif_kullanici` | True | True | Evet |
| Admin iptal etti | `iptal` | True | False | Hayır |

## Kullanıcıya Verilen Mesajlar

- E-posta doğrulanmadıysa: kullanıcıya gelen kutusunu kontrol etmesi söylenir.
- E-posta doğrulandı ama admin onayı yoksa: admin onayı beklendiği açıklanır.
- Hesap iptal edildiyse: yöneticiyle iletişime geçmesi istenir.

## Teknik Notlar

- Doğrulama kodu üretimi `view_helpers.py` içinde merkezi tutulur.
- Kod süresi `EMAIL_DOGRULAMA_KOD_SURESI_DAKIKA` ayarıyla yönetilir.
- Kodu tekrar gönderme akışı hem kayıt hem profil e-posta değişikliği için kullanılabilir.
