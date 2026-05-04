# Changelog

BookLab projesindeki önemli değişiklikler bu dosyada tutulur.

## 2026-05-04 - Ortam, Güvenlik ve Refactor Güncellemesi

### Eklendi

- Python 3.13.13 ile temiz `.venv` ortamı kuruldu.
- `.env.example` eklendi.
- `docs/10_local_setup.md` ve `docs/11_refactor_notes.md` eklendi.
- Profil e-posta değişikliği için doğrulama kodu akışı eklendi.
- Temel testler eklendi.
- Kurumsal CSS katmanı eklendi:
  - `booklab-base.css`
  - `booklab-corporate.css`
  - `pages/*.css`

### Değişti

- `views.py` konu bazlı view modüllerine ayrıldı.
- `admin.py` konu bazlı admin modüllerine ayrıldı.
- Template içindeki sayfa içi `<style>` blokları CSS dosyalarına taşındı.
- README ve dokümantasyon güncel Python/Django sürümlerine göre yenilendi.

### Düzeltildi

- `cryptography` kurulumu MSYS Python yerine Python 3.13.13 ile çözüldü.
- Pasif kullanıcı durum mesajındaki `pasif_ogrenci` / `pasif_kullanici` uyuşmazlığı giderildi.
- Randevu iptal ve admin durum değiştirme işlemleri POST + CSRF yapısına alındı.
- E-posta doğrulama kodu tekrar gönderme akışı düzeltildi.
- PDF font yolundaki kırılgan path kullanımı düzeltildi.

## 2026-02-13 - İlk Yayın

### Eklendi

- Kullanıcı kayıt ve giriş sistemi
- E-posta doğrulama mekanizması
- Pasif/aktif kullanıcı onay hiyerarşisi
- Laboratuvar ve cihaz bazlı randevu sistemi
- Admin paneli entegrasyonu
- Randevu çakışma kontrolü
- Dokümantasyon klasörü

---

[Önceki: SSS](08_faq.md) | [Ana README](../README.md)
