# 🏗️ Sistem Mimari ve Akış (Architecture & Workflow)

Bu doküman, **BookLab** sisteminin teknik bileşenlerini, veri akış diyagramlarını ve temel iş mantığı süreçlerini detaylandırır.

---

## 🧩 1. Bileşen Mimarisi (Component Diagram)

BookLab, modüler bir **MVT (Model-View-Template)** mimarisi üzerine inşa edilmiştir. Sistemin ana bileşenleri şunlardır:

1.  **Sunum Katmanı (Frontend):** - AdminLTE 3 ve Bootstrap 5 tabanlı responsive arayüz.
    - Dinamik veri gösterimi için Django Template Language (DTL).
2.  **Mantık Katmanı (Backend):** - Django 5.1 çekirdeği.
    - **Signals:** Kullanıcı kayıt anında profil oluşturma tetikleyicileri.
    - **Validators:** Form ve model seviyesinde çakışma denetleyicileri.
3.  **Veri Katmanı (Database):** - SQLite (Geliştirme) / PostgreSQL (Canlı ortam).
    - Medya ve Statik dosyalar için dosya sistemi yönetimi.

---

## 🔄 2. Temel İş Akışları

### **A. Kullanıcı Kayıt ve Onay Döngüsü**
Sistem, güvenliği ve kurumsallığı korumak için şu yolu izler:

1.  **Kayıt:** Kullanıcı bilgilerini girer (`is_active=False`).
2.  **OTP Doğrulama:** E-posta adresine gelen 6 haneli kod ile mail mülkiyeti kanıtlanır.
3.  **Onay Kuyruğu:** Profil **"Pasif Öğrenci"** statüsünde yönetici paneline düşer.
4.  **Admin Onayı:** Akademisyen/Yönetici bilgileri doğrular ve statüyü **"Aktif"** yapar.
5.  **Erişim:** Kullanıcı artık rezervasyon yapabilir hale gelir.

### **B. Rezervasyon ve Çakışma Denetimi (Conflict Logic)**
Bir randevu talebi oluşturulduğunda sistem şu algoritmayı çalıştırır:
- **Zaman Kontrolü:** Başlangıç zamanı, şu andan ve bitiş zamanından önce mi?
- **Kapasite Kontrolü:** Laboratuvarın fiziksel kapasitesi doldu mu?
- **Çakışma Sorgusu:** `Appointment.objects.filter(lab=lab, start__lt=end, end__gt=start).exists()`
- **Sonuç:** Eğer çakışma yoksa randevu onaylanır ve DB'ye yazılır.

---

## ⚙️ 3. Teknik Mekanizmalar

### **Asenkron Bildirimler**
Sistem, e-posta gönderim süreçlerini (OTP ve Şifre Sıfırlama) Django'nun e-posta motoru üzerinden yönetir. Bu sayede kullanıcıya anlık geri bildirim sağlanır.

### **Güvenlik Katmanları**
* **Middleware:** Yetkisiz kullanıcıların rezervasyon sayfalarına erişimi engellenir.
* **CSRF & XSS:** Django'nun yerleşik koruma mekanizmaları tüm formlarda aktiftir.
* **Environment Security:** Hassas veriler (API anahtarları, DB şifreleri) `.env` dosyasında izole edilmiştir.

---

## 🛠️ Mimari Avantajlar
- **Genişletilebilirlik:** Gelecekte eklenecek mobil uygulama için API katmanı (DRF) kolayca entegre edilebilir.
- **Hiyerarşik Yapı:** "Pasif-Aktif" statüsü sayesinde laboratuvar güvenliği manuel denetim altında tutulur.

---

<div align="center">

| [⬅️ Önceki Sayfa (Veritabanı Yapısı)](05_database.md) | [Sonraki Sayfa (Geliştirici Rehberi) ➡️](07_dev_guide.md) |
|:---:|:---:|

</div>

---

<div align="center">
  <sub>BookLab bir <b>Reşit ASRAV</b> projesidir. &copy; 2026</sub>
</div>