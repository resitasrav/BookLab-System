## 🔐 Güvenli Kayıt ve Çok Katmanlı Onay Sistemi

Laboratuvar güvenliğini sağlamak ve yetkisiz erişimleri engellemek amacıyla **BookLab**, çok katmanlı bir kayıt ve yetkilendirme akışı kullanır. Sisteme kayıt olan bir kullanıcının laboratuvar randevusu alabilmesi için iki aşamalı bir güvenlik duvarından geçmesi gerekir.

### 🔄 Kullanıcı Yaşam Döngüsü (User Flow)

1. 📝 **Kayıt Talebi:** Kullanıcı form doldurur. Sistem, hesabı varsayılan olarak `is_active=False` ve `Pasif Öğrenci` statüsünde oluşturur.
2. 📧 **E-Posta (OTP) Doğrulaması:** Kullanıcının mail adresine 6 haneli bir kod gönderilir. Doğrulama yapılmadan sistemde hiçbir işlem yapılamaz.
3. ⏳ **Onay Kuyruğu:** E-postasını doğrulayan kullanıcı, "Email Doğrulandı" statüsüne geçer ancak sisteme hala giriş yapamaz. Admin paneline **"Onay Bekleyen Pasif Öğrenci"** olarak düşer.
4. ✅ **Akademik Onay (Tam Erişim):** Yetkili personel, Admin paneli üzerinden öğrencinin bilgilerini teyit edip statüsünü **"Aktif Öğrenci"** (`is_active=True`) konumuna getirir. Kullanıcı artık rezervasyon yapabilir.

---

### 📊 Yetki ve Statü Matrisi

Sistemin arka planında çalışan statü yönetim tablosu aşağıdaki gibidir:

| Kullanıcı Aşaması | Sistem Statüsü (`status`) | E-Posta Onayı | Hesap (`is_active`) | Giriş İzni (Login) |
| :--- | :--- | :---: | :---: | :---: |
| **Kayıt Anı** | `pasif_ogrenci` | ❌ *False* | ❌ *False* | 🚫 Giremez |
| **E-Posta Onaylandı** | `pasif_ogrenci` | ✅ *True* | ❌ *False* | ⏳ Admin Bekleniyor |
| **Admin Onayladı** | `aktif_ogrenci` | ✅ *True* | ✅ *True* | ✅ Başarılı |
| **Admin İptal Etti** | `iptal` | ✅ *True* | ❌ *False* | 🚫 Giremez |

---

### 💡 Akıllı Kullanıcı Geri Bildirimleri
Öğrenci giriş yapmaya çalıştığında sistem, veritabanı sorgusu ile hesabın neden pasif olduğunu anlar ve spesifik geri bildirimler verir:
* *"Email adresiniz henüz doğrulanmamıştır."* (Adım 2 eksikse)
* *"Email adresiniz doğrulandı! Ancak admin tarafından onaylanmayı beklemektedir."* (Adım 4 eksikse)
* *"Hesabınız yönetici tarafından iptal edilmiştir."* (Reddedilmişse)
