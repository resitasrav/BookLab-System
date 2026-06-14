# BookLab Projesi — Claude Analiz Notları

> Bu dosya Claude'un kendi hatırlatma dosyasıdır. .gitignore'a eklenmiştir.
> Her yeni sohbette projeyi sıfırdan analiz etmek yerine buradan okuyabilirsin.

---

## 1. Proje Yapısı

```
OkulLabSistemi/
├── lab_sistemi/          # Django proje ayarları (settings, urls, wsgi)
├── rezervasyon/          # Ana uygulama
│   ├── models.py         # Tüm modeller burada
│   ├── views.py          # Sadece re-export kapısı — gerçek kodlar aşağıdaki modüllerde
│   ├── views_auth.py     # Kayıt, giriş, email doğrulama, şifre sıfırlama
│   ├── views_public.py   # Anasayfa, lab_detay
│   ├── views_calendar.py # Genel takvim, lab takvimi, events API'leri
│   ├── views_randevu.py  # Randevu al, randevularım, PDF indir, iptal
│   ├── views_management.py # Yönetim paneli, kullanıcı listesi, arıza yönetimi
│   ├── views_profile.py  # Profil düzenle, email değişim doğrulama
│   ├── view_helpers.py   # Yardımcı fonksiyonlar (check_overlap, kod üretme, mail)
│   ├── forms.py          # Django formları
│   ├── utils.py          # render_to_pdf ve benzeri araçlar
│   └── admin*.py         # Admin kayıt dosyaları (ayrıştırılmış)
├── templates/            # HTML şablonları
│   ├── base.html
│   ├── yonetim_paneli.html    # Yönetim dashboard'u (istatistik grafikleri burada)
│   ├── egitmen_paneli.html    # Günlük yoklama listesi (ayrı bir template, dikkat: şu an hiçbir view tarafından render edilmiyor!)
│   ├── randevu_form.html      # Randevu alma formu
│   └── ...diğer template'ler
└── static/css/pages/     # Sayfa bazlı CSS dosyaları
```

---

## 2. Veri Modeli (Özet)

```
Laboratuvar (id, isim, aciklama)
    └── Cihaz (id, lab_FK, isim, aktif_mi, aciklama, resim)
            └── Randevu (id, kullanici_FK, cihaz_FK, tarih, baslangic_saati,
                         bitis_saati, durum, onaylayan_admin_FK, olusturulma_zamani)
            └── Ariza  (id, kullanici_FK, cihaz_FK, aciklama, cozuldu_mu, tarih)

User (Django built-in)
    └── Profil (user_1to1, telefon, resim, dogrulama_kodu,
                email_dogrulandi, email_dogrulama_tarihi, status)

Duyuru (baslik, icerik, gorsel, kapatilabilir_mi, aktif_mi, tarih)

# Proxy modeller (sadece admin arayüzü için):
OnayBekleyenler → User proxy
AktifKullanicilar → User proxy
```

**Randevu durumları:** `onay_bekleniyor` | `onaylandi` | `reddedildi` | `geldi` | `gelmedi` | `iptal_edildi`

**Kullanıcı statüsü:** `pasif_kullanici` (email doğrulı) | `aktif_kullanici` (admin onaylı) | `iptal`

---

## 3. URL → View Haritası (Önemli Rotalar)

| URL | View | Template |
|-----|------|----------|
| `/` | `anasayfa` | `index.html` |
| `/yonetim/` | `egitmen_paneli` | `yonetim_paneli.html` |
| `/yonetim/kullanicilar/` | `kullanici_listesi` | `yonetim_kullanicilar.html` |
| `/yonetim/tum-randevular/` | `tum_randevular` | `tum_randevular.html` |
| `/yonetim/arizali-cihazlar/` | `arizali_cihaz_listesi` | `yonetim_arizali_cihazlar.html` |
| `/cihaz/<id>/` | `randevu_al` | `randevu_form.html` |
| `/randevularim/` | `randevularim` | `randevularim.html` |
| `/takvim/` | `genel_takvim` | `genel_takvim.html` |
| `/lab/<id>/` | `lab_detay` | `lab_detay.html` |
| `/api/tum-randevular/` | `tum_events_api` | JSON |
| `/api/toplu-onay/` | `toplu_onay_ajax` | JSON |

> **DİKKAT:** `urls.py` doğrudan `from rezervasyon import views` çekiyor.
> `views.py` sadece diğer modüllerden re-export yapıyor — asıl kod `views_*.py` dosyalarında.

---

## 4. Daha Önce Tespit Edilen ve Düzeltilen Hatalar

### Bug #1 — `randevu_form.html` / Dolu saatler raw kod görünümü
**Semptom:** Randevu alırken "Dolu Saatler" bölümünde bitiş saati `{{ randevu.bitis_saati|time:"H:i" }}` olarak ham kod gösteriyordu.

**Kök Neden:** Django template tokenizer'ı `{{ }}` etiketlerini satır başlarında eşleştirirken `re.DOTALL` kullanmaz. Şablon değişkeni iki satıra bölünmüştü:
```
{{ randevu.baslangic_saati|time:"H:i" }} - {{
randevu.bitis_saati|time:"H:i" }}
```

**Fix:** İkinci `{{ ... }}` aynı satıra taşındı. Ayrıca şablondaki fazladan `</p>` etiketi de temizlendi.

**Değiştirilen dosya:** `templates/randevu_form.html` (satır ~40)

---

### Bug #2 — `yonetim_paneli.html` / Lab kullanım grafiği ay filtresine uymuyordu
**Semptom:** Yönetim panelinde ay filtresi uygulandığında istatistik kartları (`toplam_randevu`, `bekleyen_onay`) doğru güncelleniyor, ama Lab Kullanım Grafiği her zaman tüm zamanın verisini gösteriyordu.

**Kök Neden:** `egitmen_paneli` view'ında `labs` queryset'i, `yil` ve `ay` değişkenleri parse edilmeden önce oluşturuluyordu:
```python
# ESKİ (yanlış sıra):
labs = Laboratuvar.objects.annotate(randevu_sayisi=_Count('cihaz__randevu'))  # filtresiz
# ... sonra yil, ay parse ediliyordu
```

**Fix:** Önce `yil`/`ay` parse edilip ardından `labs` annotation'ı `Q()` filtresiyle koşullu oluşturuluyor:
```python
# YENİ (doğru sıra):
yil = ay = None
if ay_ara:
    try:
        yil, ay = ay_ara.split('-')
    except ValueError:
        pass

if yil and ay:
    labs = Laboratuvar.objects.annotate(
        randevu_sayisi=_Count('cihaz__randevu',
            filter=Q(cihaz__randevu__tarih__year=yil, cihaz__randevu__tarih__month=ay))
    )
else:
    labs = Laboratuvar.objects.annotate(randevu_sayisi=_Count('cihaz__randevu'))
```

**Değiştirilen dosya:** `rezervasyon/views_management.py` — `egitmen_paneli()` fonksiyonu

---

## 5. Dikkat Edilmesi Gereken Diğer Noktalar

- **`egitmen_paneli.html`** template'i şu an hiçbir view tarafından render edilmiyor. `{{ randevular }}` ve `{{ bugun }}` context değişkenlerini bekliyor ama bunları gönderen bir view yok. Gelecekte ayrı bir "günlük yoklama" view'ı eklenmek istenebilir.
- **Çift import sorunu:** `views_management.py` içinde hem `from django.db.models import Count, Q` hem de `from django.db.models import Count as _Count` var. İkisi birden mevcut; `_Count` kullanımı tercih ediliyor.
- **`Randevu.save()`** override edilmiş ve `self.clean()` çağırıyor — bu, admin paneli üzerinden yapılan güncellemelerde beklenmedik `ValidationError` fırlatabilir (çakışma kontrolü yüzünden). Bilinen bir kırılganlık.
- **`ariza_bildir_genel` view'ı** sistemdeki *ilk* cihazı kullanıyor (`Cihaz.objects.first()`). Eğer sistemde cihaz yoksa bildirim yapılamıyor. Bu bir edge case.
- Proje Python **3.12+** ve Django **5.x** üzerinde çalışıyor (`.venv` içerisindeki paketlerden görülüyor).
- Line endings: Tüm template ve Python dosyaları **Windows CRLF** (`\r\n`) satır sonuyla kaydediliyor.

---

## 6. Genel İyileştirme Önerileri (Henüz Uygulanmadı)

1. **`SECRET_KEY` ve `EMAIL_*` ayarları** `.env` dosyasından okunuyor — production'da `DEBUG=False` yapılması ve `ALLOWED_HOSTS` doldurulması gerekiyor.
2. **`select_related` / `prefetch_related`** eksik: `yonetim_paneli.html` ve `randevularim.html` döngülerinde her randevu için N+1 sorgu olabilir. `Randevu.objects.select_related('kullanici', 'cihaz__lab')` eklenebilir.
3. **`randevularim` view'ı** queryset'i Python listesine çevirip filtreliyor (`[r for r in tum if ...]`). Büyük veri setlerinde bellek sorunu olabilir. Queryset seviyesinde filtrelemeye geçilmeli.
4. **Yorum satırı olarak bırakılmış kullanıcı-bazlı çakışma kontrolü** (`views_randevu.py` ~145. satır) — aktif hale getirilmesi düşünülebilir.
5. **CSRF koruması:** Tüm POST view'larında mevcut ve çalışıyor. AJAX endpoint'lerinde `X-CSRFToken` header kullanımı da doğru yapılmış.

---

### Bug #3 — PDF indirmede Türkçe karakter bozulması
**Semptom:** PDF indirildiğinde ş, ğ, ı, ö, ü gibi Türkçe karakterler bozuk veya eksik görünüş.

**Kök Neden (3 katmanda):**
1. `randevu_pdf.html`'de `@font-face` CSS kuralı yoktu. xhtml2pdf, CSS'ten fontu bulamayınca Helvetica/Times'a fallback yapıyor; bu fontlar Türkçe desteklemiyor.
2. `utils.py`'de yalnızca normal font kaydediliyordu. Bold metinler (tablo başlıkları vb.) farklı bir fonta fallback yapıyordu.
3. `settings.py`'nin sonuna yanlışlıkla eklenmiş stray `link_callback` fonksiyonu vardı.

**Fix:**
- `utils.py`: `register_fonts()` olarak yeniden yazıldı. Normal + bold için aynı DejaVuSans kaydediliyor + `registerFontFamily()` çağrısı eklendi. `link_callback` artık `staticfiles/` klasörünü de kontrol ediyor.
- `randevu_pdf.html`: `@font-face` CSS kuralı eklendi (normal ve bold için ayrı ayrı).
- `settings.py`: Sonda duran stray `link_callback` fonksiyonu silindi.

**Değiştirilen dosyalar:** `rezervasyon/utils.py`, `templates/randevu_pdf.html`, `lab_sistemi/settings.py`

---

### Bug #3b — @font-face URL yaklaşımı Windows'ta çalışmıyor (reportlab path sorunu)
**Semptom:** Bug #3 düzeltmesi için eklenen `@font-face { src: url("/static/...") }` 500 hatası verdi.

**Kök Neden:** xhtml2pdf, link_callback'ten dönen Windows yolunu (`C:\Users\...`) reportlab'a geçiriyor. reportlab bu yolda `C:` kısmını bilinmeyen URL şeması olarak yorumluyor (`unknown url type: c`) ve çöküyor.

**Doğru Fix:**
- `@font-face` template'den kaldırıldı.
- xhtml2pdf, `pdfmetrics.registerFont()` ile önceden kaydedilmiş fontları CSS `font-family` adıyla doğrudan bulabilir — `@font-face` gereksiz.
- `register_fonts()` + `registerFontFamily()` yaklaşımı (utils.py'deki) yeterli ve doğru.
- Bold Türkçe metin için `registerFontFamily('DejaVuSans', normal='DejaVuSans', bold='DejaVuSans-Bold')` kayıt yapılıyor.

**Değiştirilen dosya:** `templates/randevu_pdf.html` (@font-face bloğu kaldırıldı)

**KURAL: xhtml2pdf + Windows + reportlab = @font-face ile dosya yolu KULLANMA.**

### Bug #3c — pdfmetrics.registerFont() tek başına yetmiyor (CSS çözümlemesi çalışmıyor)
**Semptom:** Bug #3b düzeltmesinden sonra PDF indiriyor ama Türkçe karakterler hâlâ bozuk.

**Kök Neden:** xhtml2pdf'nin CSS işleyicisi (`pisaDocument`) pdfmetrics'e önceden kaydedilmiş fontları CSS `font-family` üzerinden her zaman güvenilir şekilde bulamıyor. Özellikle xhtml2pdf 0.2.x sürümlerinde CSS font çözümlemesi @font-face veya link_callback'e bağımlı; sadece registerFont() yeterli değil.

**Doğru Fix:** Fontu `data:` URI olarak Python tarafında HTML stringine enjekte et. reportlab `data:` URI'leri natively destekliyor (Windows yol sorunu yok), bu yüzden link_callback'e ihtiyaç kalmıyor.

```python
# render_to_pdf() içinde, html = template.render(...) sonrasına eklendi:
import base64
font_path = _find_font_path("DejaVuSans.ttf")
if font_path:
    with open(font_path, "rb") as f:
        font_b64 = base64.b64encode(f.read()).decode("ascii")
    font_css = (
        "<style>\n"
        "@font-face {\n"
        "    font-family: 'DejaVuSans';\n"
        f"    src: url(\"data:font/truetype;base64,{font_b64}\");\n"
        "    font-weight: normal;\n"
        "}\n"
        "@font-face {\n"
        "    font-family: 'DejaVuSans';\n"
        f"    src: url(\"data:font/truetype;base64,{font_b64}\");\n"
        "    font-weight: bold;\n"
        "}\n"
        "</style>"
    )
    html = html.replace("</head>", font_css + "\n</head>", 1)
```

**Değiştirilen dosya:** `rezervasyon/utils.py` — `render_to_pdf()` fonksiyonu

**KURAL: xhtml2pdf + Windows + reportlab = @font-face ile DOSYA YOLU kullanma, ama `data:` URI'si ile @font-face kullanmak sorunsuz çalışır.**
