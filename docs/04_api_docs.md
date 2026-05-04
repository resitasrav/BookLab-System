# API ve Backend Notları

BookLab şu anda klasik Django MVT yapısıyla çalışır. Projede REST framework tabanlı tam bir public API yoktur; ancak takvim ve yönetim ekranları için JSON endpointleri bulunur.

## Mevcut Endpointler

| Endpoint | Method | Açıklama | Yetki |
| :--- | :--- | :--- | :--- |
| `/api/onay-bekleyen-sayisi/` | GET | Pasif kullanıcı, bekleyen randevu ve açık arıza sayılarını döner | Staff |
| `/api/tum-randevular/` | GET | Genel takvim için randevu event listesini döner | Giriş gerekli |
| `/api/lab/<lab_id>/events/` | GET | Belirli laboratuvarın takvim eventlerini döner | Giriş gerekli |

## Sayfa Bazlı Backend Akışları

| URL | Method | Açıklama |
| :--- | :--- | :--- |
| `/kayit/` | GET/POST | Kullanıcı kayıt başlatma |
| `/email-dogrulama/` | GET/POST | Kayıt e-posta kod doğrulaması |
| `/kod-tekrar-gonder/` | GET | Kayıt veya e-posta değişikliği için yeni kod gönderme |
| `/profil/email-dogrula/` | GET/POST | Profil e-posta değişikliği doğrulama |
| `/cihaz/<cihaz_id>/` | GET/POST | Cihaz için randevu alma |
| `/iptal/<randevu_id>/` | POST | Kullanıcının kendi randevusunu iptal etmesi |
| `/durum-degis/<randevu_id>/<yeni_durum>/` | POST | Staff kullanıcının randevu durumunu değiştirmesi |
| `/yonetim/toplu-islem/` | POST | Staff kullanıcının seçili randevulara toplu işlem uygulaması |
| `/yonetim/cihaz-durum/<cihaz_id>/` | POST | Staff kullanıcının cihazı aktif/pasif yapması |

## Randevu Çakışma Mantığı

Randevu çakışması cihaz ve tarih bazında kontrol edilir. Aktif sayılan durumlar:

- `onay_bekleniyor`
- `onaylandi`
- `geldi`

Mantık:

```python
Randevu.objects.filter(
    cihaz=cihaz,
    tarih=tarih,
    durum__in=[Randevu.ONAY_BEKLENIYOR, Randevu.ONAYLANDI, Randevu.GELDI],
    baslangic_saati__lt=bitis,
    bitis_saati__gt=baslangic,
).exists()
```

## Güvenlik Notları

- Durum değiştiren işlemler POST ile çalışır.
- CSRF token template formlarında kullanılmalıdır.
- API endpointleri Django session/auth korumasına dayanır.
- Gelecekte mobil uygulama veya dış entegrasyon hedeflenirse ayrı bir DRF/JWT katmanı planlanmalıdır.

---

[Önceki: Yönetici Rehberi](03_admin_guide.md) | [Sonraki: Veritabanı](05_database.md)
