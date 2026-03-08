# ⚙️ API & Backend Dokümantasyonu

Bu doküman, **BookLab** sisteminin veri iletişim katmanını, yetkilendirme mantığını ve backend iş süreçlerini (business logic) detaylandırır.

---

## 🔐 Yetkilendirme (Authentication & Authorization)

Sistem, güvenliği en üst düzeyde tutmak için katmanlı bir yetkilendirme yapısı kullanır.

* **Session-Based (MVT):** Mevcut web arayüzünde Django'nun güvenli session yapısı kullanılmaktadır.
* **JWT (JSON Web Token):** API entegrasyonları için (mobil uygulama vb.) JWT tabanlı yetkilendirme mimarisi planlanmıştır.
* **Yetki Seviyeleri:**
    * `Unauthenticated`: Sadece giriş ve kayıt sayfalarına erişim.
    * `Passive Student`: Sadece profil doğrulama ve onay bekleme ekranı.
    * `Active Student`: Rezervasyon yapma ve takvim görüntüleme.
    * `Admin / Staff`: Tüm CRUD işlemlerine tam erişim.

---

## 🌐 API Endpoint Listesi (Geliştirici Referansı)

Sistemin veri akışını sağlayan temel API uç noktaları aşağıda listelenmiştir.

### **1. Kullanıcı İşlemleri**

| Endpoint | Method | Açıklama | Yetki |
| :--- | :--- | :--- | :--- |
| `/api/users/` | **GET** | Tüm kayıtlı kullanıcıları listeler. | Admin |
| `/api/users/{id}/` | **GET** | Belirli bir kullanıcının profil detaylarını getirir. | Admin / Sahibi |
| `/api/users/me/` | **GET** | Giriş yapmış kullanıcının profil bilgilerini döner. | Aktif Kullanıcı |

### **2. Rezervasyon ve Takvim İşlemleri**

| Endpoint | Method | Açıklama | Yetki |
| :--- | :--- | :--- | :--- |
| `/api/reservations/` | **GET** | Mevcut tüm rezervasyonları (takvim verisi) döner. | Herkes |
| `/api/reservations/` | **POST** | Yeni bir laboratuvar/cihaz randevusu oluşturur. | Aktif Öğrenci |
| `/api/reservations/{id}/` | **DELETE** | Mevcut bir randevuyu iptal eder. | Sahibi / Admin |

---

## 🧠 Backend Mantığı (Business Logic)

BookLab'in kalbinde yer alan iki kritik algoritma aşağıda açıklanmıştır:

### **A. Akıllı Çakışma Kontrolü (Conflict Prevention)**
Yeni bir randevu talebi (`POST`) geldiğinde sistem şu kontrolü yapar:
```python
# Yeni randevunun mevcut randevularla zaman kesişimi sorgusu
is_conflict = Appointment.objects.filter(
    lab=requested_lab,
    start_time__lt=requested_end_time,
    end_time__gt=requested_start_time
).exists()

if is_conflict:
    raise ValidationError("Bu saat dilimi zaten dolu!")