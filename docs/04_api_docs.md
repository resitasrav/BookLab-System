# API Dokümantasyonu

## Kullanıcı Endpoint’leri
| Endpoint | Method | Açıklama |
|----------|--------|----------|
| /api/users/ | GET | Tüm kullanıcıları listeler |
| /api/users/{id}/ | GET | Belirli kullanıcıyı gösterir |
| /api/reservations/ | POST | Yeni rezervasyon oluşturur |

## Yetkilendirme
- JWT Token kullanımı
- Admin kullanıcılar tüm endpoint’lere erişebilir
