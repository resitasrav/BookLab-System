# Veritabanı Yapısı

BookLab geliştirme ortamında SQLite kullanır. Modeller `rezervasyon/models.py` içinde tanımlıdır.

## Ana Modeller

### Laboratuvar

Laboratuvar bilgisini tutar.

| Alan | Açıklama |
| :--- | :--- |
| `isim` | Laboratuvar adı |
| `aciklama` | Laboratuvar açıklaması |

İlişki:

- Bir laboratuvarın birden fazla cihazı olabilir.

### Cihaz

Randevu alınabilen cihazı temsil eder.

| Alan | Açıklama |
| :--- | :--- |
| `lab` | Bağlı olduğu laboratuvar |
| `isim` | Cihaz adı |
| `aktif_mi` | Kullanıma açık mı |
| `aciklama` | Cihaz açıklaması veya bakım notu |
| `resim` | Cihaz görseli |

İlişki:

- Bir cihaz bir laboratuvara bağlıdır.
- Bir cihazın birden fazla randevusu ve arıza kaydı olabilir.

### Randevu

Cihaz bazlı rezervasyon bilgisini tutar.

| Alan | Açıklama |
| :--- | :--- |
| `kullanici` | Randevuyu alan kullanıcı |
| `cihaz` | Seçilen cihaz |
| `tarih` | Randevu tarihi |
| `baslangic_saati` | Başlangıç saati |
| `bitis_saati` | Bitiş saati |
| `durum` | Randevu durumu |
| `onaylayan_admin` | İşlemi yapan yönetici |

Durumlar:

- `onay_bekleniyor`
- `onaylandi`
- `reddedildi`
- `geldi`
- `gelmedi`
- `iptal_edildi`

### Profil

Django `User` modeline bire bir bağlı ek kullanıcı bilgisidir.

| Alan | Açıklama |
| :--- | :--- |
| `user` | Django kullanıcı bağlantısı |
| `okul_numarasi` | Okul numarası |
| `telefon` | Telefon numarası |
| `resim` | Profil resmi |
| `dogrulama_kodu` | Eski/uyumluluk doğrulama kodu alanı |
| `kod_olusturma_tarihi` | Kod oluşturma tarihi |
| `status` | Kullanıcı statüsü |
| `email_dogrulandi` | E-posta doğrulandı mı |
| `email_dogrulama_tarihi` | Doğrulama zamanı |

Profil statüleri:

- `pasif_kullanici`
- `aktif_kullanici`
- `iptal`

### Ariza

Cihaz arıza veya bakım bildirimlerini tutar.

| Alan | Açıklama |
| :--- | :--- |
| `kullanici` | Bildiren kullanıcı |
| `cihaz` | İlgili cihaz |
| `aciklama` | Arıza açıklaması |
| `cozuldu_mu` | Arıza çözüldü mü |
| `tarih` | Bildirim tarihi |

### Duyuru

Ana sayfada gösterilen duyuruları tutar.

| Alan | Açıklama |
| :--- | :--- |
| `baslik` | Duyuru başlığı |
| `icerik` | Duyuru içeriği |
| `aktif_mi` | Yayında mı |
| `tarih` | Oluşturma tarihi |

## Proxy Modeller

Admin panelini daha kullanışlı yapmak için proxy modeller kullanılır:

- `OnayBekleyenler`
- `AktifKullanicilar`

Bu modeller ayrı tablo oluşturmaz; Django `User` modelini farklı admin listeleriyle gösterir.

---

[Önceki: API ve Backend](04_api_docs.md) | [Sonraki: Mimari](06_architecture.md)
