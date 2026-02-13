# Veritabanı Yapısı

## Modeller
- **User:** Kullanıcı bilgileri, statü, rol
- **Lab:** Laboratuvar bilgileri
- **Device:** Cihazlar ve detayları
- **Reservation:** Randevu bilgileri ve zamanlama

## İlişkiler
- User → Reservation (1:N)
- Lab → Device (1:N)
- Device → Reservation (1:N)
