# 🏗️ Sistem Mimari ve Akış (Architecture & Workflow)

Bu doküman, **BookLab** sisteminin teknik bileşenlerini, veri akış diyagramlarını ve kullanıcı süreçlerini detaylandırır.

---

## 🧩 1. Bileşen Mimarisi (Component Diagram)

BookLab, modüler bir yapıya sahip olup temel olarak üç ana katmandan oluşur:

1.  **Frontend (Sunum Katmanı):** AdminLTE ve Bootstrap 5 kullanılarak oluşturulan, kullanıcı ve yönetici arayüzleri.
2.  **Backend (Mantık Katmanı):** Django framework üzerinde çalışan, yetkilendirme, rezervasyon kontrolü ve e-posta tetikleyicilerini içeren çekirdek yapı.
3.  **Data (Veri Katmanı):** SQLite/PostgreSQL üzerinde koşan, ilişkisel veri modelleri ve statik/medya dosyaları.

---

## 🔄 2. Temel İş Akışları

### **A. Kullanıcı Kayıt ve Onay Akışı**
Sistem, güvenliği sağlamak için çok aşamalı bir doğrulama süreci izler:

```mermaid
graph TD
    A[Öğrenci Kayıt Olur] --> B{E-posta Doğrulama}
    B -- Yanlış Kod --> B
    B -- Doğru Kod --> C[Profil 'Pasif' Statüsüne Alınır]
    C --> D[Admin Paneline Bildirim Düşer]
    D --> E{Admin Onayı}
    E -- Red --> F[Hesap Askıya Alınır]
    E -- Onay --> G[Profil 'Aktif' Statüsüne Geçer]
    G --> H[Randevu Alma Erişimi Açılır]