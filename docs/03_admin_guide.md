# 🔐 Yönetici / Akademisyen Kılavuzu

Bu rehber, laboratuvar sorumluları ve akademisyenlerin **BookLab** yönetim panelini (AdminLTE) kullanarak sistemi nasıl denetleyeceğini ve yöneteceğini açıklar.

---

## 👨‍💼 1. Kullanıcı ve Profil Yönetimi

Sistemin güvenliği, kullanıcıların statüleri üzerinden kontrol edilir. Her yeni kayıt, yönetici onayına düşer.

### **Kullanıcı Onay Süreci (Pasiften Aktife)**
1.  **Dashboard Üzerinden Takip:** Yönetim panelinde "Onay Bekleyen Kullanıcılar" sekmesine gidin.
2.  **Statü Kontrolü:** `Pasif Öğrenci` statüsündeki kullanıcıların bilgilerini (okul numarası, e-posta) inceleyin.
3.  **Onaylama:** Kullanıcıyı seçerek statüsünü `Aktif Öğrenci` olarak güncelleyin.
4.  **Sistem Erişimi:** Bu işlem sonucunda kullanıcının `is_active` değeri `True` olur ve sisteme giriş yapabilir hale gelir.

### **Toplu İşlemler**
- Admin panelindeki listeleme sayfasında birden fazla kullanıcı seçerek **"Toplu Aktif Et"** veya **"Statü Değiştir"** eylemlerini saniyeler içinde gerçekleştirebilirsiniz.

---

## 📅 2. Merkezi Rezervasyon Kontrolü

Laboratuvar trafiğini yönetmek ve çakışmaları önlemek için tasarlanmış merkezi kontrol sistemidir.

- **Tüm Randevuları Listeleme:** Hangi laboratuvarın, hangi cihazın, hangi öğrenci tarafından ne zaman rezerve edildiğini tek bir tabloda görün.
- **Manuel Müdahale:** Gerekli durumlarda (bakım, acil durum vb.) onaylanmış bir randevuyu iptal edebilir veya saatlerini güncelleyebilirsiniz.
- **Çakışma Denetimi:** Sistem çakışmaları otomatik önlese de, yönetici olarak özel durumlar için esnek tanımlamalar yapabilirsiniz.

---

## 📊 3. Raporlama ve İstatistikler

Laboratuvar kaynaklarının verimli kullanılıp kullanılmadığını analiz etmek için raporlama araçlarını kullanın.

- **Kullanım İstatistikleri:** En çok tercih edilen laboratuvarları ve en sık kullanılan cihazları (3D Yazıcı, CNC vb.) grafiklerle analiz edin.
- **Dışa Aktarma:** Randevu listelerini veya kullanıcı dökümlerini **Excel** veya **PDF** formatında dışa aktararak akademik raporlarınıza ekleyebilirsiniz.
- **Filtreleme:** Tarih aralığına, laboratuvar adına veya öğrenci statüsüne göre gelişmiş aramalar yapın.

---

## 📢 4. Bildirim ve Sistem Yönetimi

- **E-Posta Kontrolü:** Sistem tarafından gönderilen OTP (doğrulama) kodlarının ve bilgilendirme maillerinin durumunu takip edin.
- **Toplu Duyuru:** Gerektiğinde kayıtlı tüm aktif öğrencilere laboratuvar kuralları veya duyurular hakkında toplu bilgilendirme e-postası gönderebilirsiniz.

---

## 💡 Yönetici İpuçları
* **Cihaz Durumları:** Bir cihaz arızalandığında, randevu alınmasını engellemek için cihaz durumunu "Arızalı" olarak işaretlemeyi unutmayın.
* **Log Takibi:** Sistemdeki tüm silme ve güncelleme işlemleri kayıt altına alınmaktadır (Admin Log).

---

<div align="center">

| [⬅️ Önceki Sayfa (Kullanıcı Kılavuzu)](02_user_guide.md) | [Sonraki Sayfa (API & Backend) ➡️](04_api_docs.md) |
|:---:|:---:|

</div>

---

<div align="center">
  <sub>BookLab bir <b>Reşit ASRAV</b> projesidir. &copy; 2026</sub>
</div>