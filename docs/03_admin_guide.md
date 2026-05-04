# Yönetici Rehberi

Bu rehber laboratuvar sorumluları, akademisyenler ve sistem yöneticileri için hazırlanmıştır.

## Yönetim Ekranları

BookLab'de iki yönetim yüzeyi bulunur:

- Uygulama içi yönetim paneli: `/yonetim/`
- Django/Jazzmin admin paneli: `/admin/`

## Kullanıcı Onayı

Yeni kullanıcılar e-posta doğrulamasından sonra admin onayına düşer.

Yönetici yapılacak işlemler:

1. Onay bekleyen kullanıcıyı incele.
2. E-posta, ad-soyad, telefon ve gerekiyorsa okul numarasını kontrol et.
3. Uygunsa kullanıcıyı aktif et.
4. Uygun değilse pasif bırak veya iptal statüsüne çek.

Profil statüleri:

- `pasif_kullanici`: E-posta doğrulanmış, admin bekliyor.
- `aktif_kullanici`: Sisteme giriş yapabilir.
- `iptal`: Kullanıcı erişimi kapalıdır.

## Randevu Yönetimi

Yönetici randevular üzerinde şu işlemleri yapabilir:

- Onayla
- Reddet
- Geldi olarak işaretle
- Gelmedi olarak işaretle
- Toplu işlem uygula
- Filtreleme ve arama yap

Durum değiştiren işlemler POST + CSRF ile çalışır. Bu, yanlışlıkla link tıklaması veya dış istekle durum değişmesini engeller.

## Cihaz ve Arıza Yönetimi

Cihaz arızalandığında:

1. Cihaz pasife alınır.
2. Açık arıza kaydı oluşturulur.
3. Cihaz randevu alınamaz hale gelir.
4. Cihaz tekrar aktife alınırsa açık arızalar çözüldü olarak işaretlenir.

## Duyurular

Admin panelinden duyuru oluşturulabilir ve aktif/pasif yapılabilir. Aktif duyurular ana sayfada görüntülenir.

## Raporlama

- Randevu listeleri filtrelenebilir.
- Randevular CSV olarak dışa aktarılabilir.
- Kullanıcı kendi randevularını PDF olarak indirebilir.
- Yönetim panelinde laboratuvar bazlı kullanım grafiği bulunur.

---

[Önceki: Kullanıcı Kılavuzu](02_user_guide.md) | [Sonraki: API ve Backend](04_api_docs.md)
