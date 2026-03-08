# 🗄️ Veritabanı Yapısı (Database Schema)

Bu doküman, **BookLab** sisteminin veri tabanı mimarisini, modeller arası ilişkileri ve tablo yapılarını detaylandırır. Sistem, ilişkisel veri tabanı mantığı üzerine inşa edilmiştir.

---

## 🗺️ Veri Modeli İlişkileri (ER Summary)

BookLab veri modeli, yüksek tutarlılık ve ölçeklenebilirlik için tasarlanmıştır:
- **User ↔ Profil:** One-to-One (Bire bir) ilişki.
- **Lab ↔ Cihaz:** One-to-Many (Bire çok) ilişki.
- **Appointment ↔ User, Lab, Cihaz:** Many-to-One (Çoktan bire) ilişki.

---

## 📋 Tablo Detayları

### 1. Profil Modeli (`rezervasyon_profil`)
Kullanıcıya ait ek bilgileri ve sistem statüsünü saklar. Django'nun yerleşik `User` modeli ile bire bir bağlıdır.

| Alan | Tip | Açıklama |
| :--- | :--- | :--- |
| `user` | OneToOneField | Django Auth User bağlantısı |
| `okul_numarasi` | CharField | Öğrencinin benzersiz okul numarası |
| `status` | ChoiceField | Pasif Öğrenci, Aktif Öğrenci, İptal |
| `email_dogrulandi` | BooleanField | OTP doğrulama durumu |
| `kod_olusturma_tarihi`| DateTimeField | OTP kodunun geçerlilik süresi için |

### 2. Laboratuvar Modeli (`rezervasyon_lab`)
Rezervasyon yapılabilen fiziksel alanları temsil eder.

| Alan | Tip | Açıklama |
| :--- | :--- | :--- |
| `ad` | CharField | Laboratuvarın adı (örn: Robotik Lab) |
| `konum` | CharField | Oda numarası veya blok bilgisi |
| `kapasite` | IntegerField | Aynı anda bulunabilecek max kişi |

### 3. Cihaz Modeli (`rezervasyon_cihaz`)
Laboratuvar içindeki spesifik ekipmanları temsil eder.

| Alan | Tip | Açıklama |
| :--- | :--- | :--- |
| `lab` | ForeignKey | Bağlı olduğu laboratuvar |
| `cihaz_adi` | CharField | Cihazın adı (örn: 3D Yazıcı - Zortrax) |
| `durum` | ChoiceField | Aktif, Arızalı, Bakımda |

### 4. Randevu Modeli (`rezervasyon_appointment`)
Tüm rezervasyon verilerinin tutulduğu merkezi tablodur.

| Alan | Tip | Açıklama |
| :--- | :--- | :--- |
| `user` | ForeignKey | Randevuyu alan öğrenci |
| `lab` | ForeignKey | Rezerve edilen alan |
| `cihaz` | ForeignKey | Rezerve edilen cihaz (Opsiyonel) |
| `start_time` | DateTimeField | Başlangıç zamanı |
| `end_time` | DateTimeField | Bitiş zamanı |

---

## 🛠️ Veritabanı Optimizasyonu

* **Index Kullanımı:** `start_time` ve `end_time` alanları üzerinde, randevu çakışma sorgularını hızlandırmak için indeksleme yapılmıştır.
* **Cascade Deletion:** Bir kullanıcı silindiğinde, ona ait profil verileri `on_delete=models.CASCADE` ile otomatik olarak temizlenir.
* **Validation:** Veritabanı seviyesinde `CheckConstraint` kullanılarak bitiş zamanının başlangıç zamanından önce olması engellenmiştir.

---

<div align="center">

| [⬅️ Önceki Sayfa (API & Backend)](04_api_docs.md) | [Sonraki Sayfa (Sistem Mimari ve Akış) ➡️](06_architecture.md) |
|:---:|:---:|

</div>

---

<div align="center">
  <sub>BookLab bir <b>Reşit ASRAV</b> projesidir. &copy; 2026</sub>
</div>