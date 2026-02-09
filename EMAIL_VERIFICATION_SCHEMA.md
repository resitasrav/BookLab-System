# 📧 EMAIL DOĞRULAMA VE KAYIT AKIŞI - ŞABLON PLANI

## **AMAÇ**
- ❌ Email doğrulanmazsa = Kayıt YAPıLMAYACak (Hesap oluşturulmayacak)
- ✅ Email doğrulanırsa = Kayıt "Pasif Öğrenci" durumunda yapılacak
- 🔐 Sadece Admin = "Pasif Öğrenci" → "Aktif Öğrenci" değiştirebilir

---

## **PHASE 1: Profil Model'e Status Ekle**

### ❌ MEVCUT KODLAR:
```python
# models.py Line 127
class Profil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    okul_numarasi = models.CharField(max_length=20, blank=True)
    telefon = models.CharField(max_length=15, blank=True)
    resim = models.ImageField(upload_to="profil_resimleri/", blank=True, null=True)
    dogrulama_kodu = models.CharField(max_length=6, blank=True, null=True)
```

### ✅ YENİ KODLAR:
```python
# models.py - EKLENECEK
class Profil(models.Model):
    # OGRENCİ STATUS SEÇENEKLERI
    STATUS_CHOICES = [
        ('pasif_ogrenci', 'Pasif Öğrenci (Email Doğrulı)'),
        ('aktif_ogrenci', 'Aktif Öğrenci (Admin Onaylı)'),
        ('iptal', 'İptal Edildi'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    okul_numarasi = models.CharField(max_length=20, blank=True)
    telefon = models.CharField(max_length=15, blank=True)
    resim = models.ImageField(upload_to="profil_resimleri/", blank=True, null=True)
    dogrulama_kodu = models.CharField(max_length=6, blank=True, null=True)
    
    # ✨ YENİ ALANLAR:
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pasif_ogrenci',
        verbose_name="Öğrenci Durumu"
    )
    email_dogrulandi = models.BooleanField(default=False, verbose_name="Email Doğrulandı mı?")
    email_dogrulama_tarihi = models.DateTimeField(null=True, blank=True)
```

---

## **PHASE 2: Kayıt View'ı Yeniden Yaz**

### ❌ ESKI AKIŞ:
```
Kayıt POST
  ↓
is_active = False
  ↓
Session'a Kod + User ID
  ↓
Email Gönder
  ↓
email_dogrulama sayfasına yönlendir
```

### ✅ YENİ AKIŞ:
```
Kayıt POST
  ↓
USER OLUŞTURMA: is_active = False (Asla login yapamaz)
  ↓
PROFIL OLUŞTURMA:
  - status = 'pasif_ogrenci'
  - email_dogrulandi = False
  ↓
Session'a Kod + User ID
  ↓
Email Gönder
  ↓
email_dogrulama sayfasına yönlendir
```

### 📝 KOD:
```python
# views.py - kayit() fonksiyonu
def kayit(request):
    if request.method == "POST":
        form = KayitFormu(request.POST)
        if form.is_valid():
            # ✅ ADIM 1: User Oluştur (PASİF)
            user = form.save(commit=False)
            user.is_active = False  # 🔴 Asla aktif OLMAYACAK
            user.save()
            
            # ✅ ADIM 2: Profil Oluştur ve Durumunu Belirle
            # (post_save signal ile otomatik oluşturulur, ama durumunu set et)
            profil = Profil.objects.get(user=user)
            profil.status = 'pasif_ogrenci'  # ← YENİ
            profil.email_dogrulandi = False  # ← YENİ
            profil.save()
            
            # ✅ ADIM 3: Doğrulama Kodu Üret
            dogrulama_kodu = str(random.randint(100000, 999999))
            request.session['dogrulama_kodu'] = dogrulama_kodu
            request.session['dogrulama_user_id'] = user.id
            
            # ✅ ADIM 4: Email Gönder
            try:
                send_mail(
                    "BTÜ Lab Kayıt Doğrulama",
                    f"Doğrulama kodunuz: {dogrulama_kodu}",
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False
                )
                messages.success(
                    request, 
                    "✅ Kayıt başarılı! Lütfen mailine gelen kodu gir."
                )
                return redirect("email_dogrulama")
            
            except Exception as e:
                # ⚠️ EMAIL HATA DURUMU
                messages.error(
                    request, 
                    f"❌ Email gönderilemedi. Lütfen yöneticiye başvurun."
                )
                # Kullanıcı silme (Başarısız kayıt)
                user.delete()  # ← BU ÖNEMLİ!
                return render(request, "kayit.html", {"form": KayitFormu()})
    
    else:
        form = KayitFormu()
    
    return render(request, "kayit.html", {"form": form})
```

---

## **PHASE 3: Email Doğrulama View'ı Güncelle**

### ✅ KOD:
```python
# views.py - email_dogrulama() fonksiyonu
def email_dogrulama(request):
    user_id = request.session.get('dogrulama_user_id')
    dogrulama_kodu = request.session.get('dogrulama_kodu')
    
    # ❌ Session'da veri yoksa kayıt sayfasına gönder
    if not user_id or not dogrulama_kodu:
        messages.error(request, "❌ Oturum süresi dolmuş. Lütfen tekrar kayıt olun.")
        return redirect("kayit")

    if request.method == "POST":
        girilen_kod = request.POST.get("kod").strip()
        
        # ✅ KOD DOĞRU MU?
        if girilen_kod == dogrulama_kodu:
            user = get_object_or_404(User, id=user_id)
            
            # ✨ PROFIL'İ GÜNCELLE
            profil = Profil.objects.get(user=user)
            profil.email_dogrulandi = True  # ← EMAIL DOĞRULANDI
            profil.email_dogrulama_tarihi = timezone.now()
            profil.status = 'pasif_ogrenci'  # ← PASIF ÖĞRENCI
            profil.save()
            
            # 🔴 USER ASLA AKTİF OLMAYACAK (Admin Karar Verecek)
            # user.is_active = True  ← YAPMIYORUZ!
            
            # 🗑️ Session'da Verileri Sil
            del request.session['dogrulama_user_id']
            del request.session['dogrulama_kodu']
            
            messages.success(
                request, 
                "🎉 Email doğrulandı! Admin tarafından onaylanmayı beklemektedir."
            )
            return redirect("giris")
        
        else:
            # ❌ KOD YANLIŞ
            messages.error(request, "❌ Hatalı doğrulama kodu.")
            # Session kalır, tekrar deneyebilir

    return render(request, "email_dogrulama.html")
```

---

## **PHASE 4: Giriş View'ı Güncelle (is_active Check)**

### ✅ KOD:
```python
# views.py - CustomLoginView

class CustomLoginView(auth_views.LoginView):
    template_name = "giris.html"
    form_class = EmailOrUsernameAuthenticationForm

    def form_invalid(self, form):
        identifier = self.request.POST.get("username", "").strip()
        pasif_mesaj = None
        
        if identifier:
            user_qs = User.objects.filter(username__iexact=identifier) | \
                      User.objects.filter(email__iexact=identifier)
            user = user_qs.first()
            
            if user and not user.is_active:
                # ➡️ DETAY EKRANINDA: Profil'e bakarak neden pasif olduğunu söyle
                try:
                    profil = Profil.objects.get(user=user)
                    
                    if not profil.email_dogrulandi:
                        # Email doğrulanmamışsa
                        pasif_mesaj = (
                            "❌ Email adresiniz henüz doğrulanmamıştır. "
                            "Kayıt sırasında gönderilen doğrulama kodunu "
                            "email_dogrulama sayfasında girmelisiniz."
                        )
                    elif profil.status == 'pasif_ogrenci':
                        # Email doğrulı ama admin onaylamadı
                        pasif_mesaj = (
                            "⏳ Email adresiniz doğrulandı! "
                            "Ancak admin tarafından onaylanmayı beklemektedir. "
                            "Lütfen daha sonra tekrar deneyin."
                        )
                    elif profil.status == 'iptal':
                        # Hesabı iptal edildi
                        pasif_mesaj = (
                            "🚫 Hesabınız yönetici tarafından iptal edilmiştir. "
                            "Lütfen yöneticiye başvurun."
                        )
                
                except Profil.DoesNotExist:
                    pasif_mesaj = (
                        "❌ Profil bilgisi bulunamadı. "
                        "Lütfen yöneticiye başvurun."
                    )

        context = self.get_context_data(form=form)
        if pasif_mesaj:
            context["pasif_mesaj"] = pasif_mesaj
        return self.render_to_response(context)
```

---

## **PHASE 5: Admin Panel'de Öğrenci Listesi**

### ✅ KOD (admin.py):
```python
# admin.py - Profil Admin

from django.utils.html import format_html
from django.contrib import admin

class ProfilAdmin(admin.ModelAdmin):
    list_display = [
        'user_username',
        'okul_numarasi',
        'status_badge',
        'email_dogrulandi_display',
        'email_dogrulama_tarihi',
    ]
    
    list_filter = [
        'status',
        'email_dogrulandi',
        'email_dogrulama_tarihi',
    ]
    
    search_fields = [
        'user__username',
        'user__email',
        'okul_numarasi',
    ]
    
    readonly_fields = [
        'email_dogrulama_tarihi',
        'email_dogrulandi',
    ]
    
    fieldsets = (
        ('Kullanıcı Bilgisi', {
            'fields': ('user', 'okul_numarasi', 'telefon', 'resim')
        }),
        ('Email Doğrulama', {
            'fields': ('email_dogrulandi', 'email_dogrulama_tarihi')
        }),
        ('Öğrenci Durumu', {
            'fields': ('status',),
            'description': '⚠️ SADECE BURADAN "Pasif Öğrenci" → "Aktif Öğrenci" değiştirebilirsiniz.'
        }),
    )
    
    actions = ['make_active_ogrenci', 'make_pasif_ogrenci']
    
    def user_username(self, obj):
        return obj.user.username
    user_username.short_description = "Kullanıcı Adı"
    
    def status_badge(self, obj):
        colors = {
            'pasif_ogrenci': '#FFC107',      # Sarı
            'aktif_ogrenci': '#28A745',      # Yeşil
            'iptal': '#DC3545',              # Kırmızı
        }
        color = colors.get(obj.status, '#6C757D')
        status_text = obj.get_status_display()
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; '
            'border-radius: 5px; font-weight: bold;">{}</span>',
            color, status_text
        )
    status_badge.short_description = "Durum"
    
    def email_dogrulandi_display(self, obj):
        if obj.email_dogrulandi:
            return format_html('✅ Doğrulı')
        return format_html('❌ Doğrulanmamış')
    email_dogrulandi_display.short_description = "Email Durumu"
    
    def make_active_ogrenci(self, request, queryset):
        updated = queryset.update(status='aktif_ogrenci')
        self.message_user(
            request, 
            f'{updated} öğrenci "Aktif Öğrenci" durumuna alındı.'
        )
    make_active_ogrenci.short_description = "✅ Aktif Öğrenci Yap"
    
    def make_pasif_ogrenci(self, request, queryset):
        updated = queryset.update(status='pasif_ogrenci')
        self.message_user(
            request, 
            f'{updated} öğrenci "Pasif Öğrenci" durumuna alındı.'
        )
    make_pasif_ogrenci.short_description = "⏳ Pasif Öğrenci Yap"

admin.site.register(Profil, ProfilAdmin)
```

---

## **PHASE 6: Migration Oluştur**

### 📝 KOMUTLAR:
```bash
# 1. Migration dosyası oluştur
python manage.py makemigrations

# 2. Migration'ı yükle
python manage.py migrate

# 3. Mevcut kullanıcıları kontrol et
python manage.py shell
>>> from rezervasyon.models import Profil
>>> Profil.objects.all().update(email_dogrulandi=False, status='pasif_ogrenci')
```

---

## **PHASE 7: Test Senaryoları**

### **TEST 1: Email Doğrulama Başarılı**
```
1. Kayıt Formuna Gir
   ✅ Form Valid
   ✅ User Oluştur (is_active=False)
   ✅ Profil Oluştur (status=pasif_ogrenci, email_dogrulandi=False)
   ✅ Email Gönder
   ✅ email_dogrulama sayfasına yönlendir

2. Email Doğrulama Kodunu Gir
   ✅ Kod Doğru
   ✅ Profil.status = pasif_ogrenci
   ✅ Profil.email_dogrulandi = True
   ✅ User.is_active KALIR False ← ÖNEMLİ
   ✅ "Email doğrulandı! Admin onayını bekleyin" mesajı
   ✅ Giriş sayfasına yönlendir

3. Giriş Sayfasında
   ❌ Giriş BAŞARILI DEĞİL (is_active=False)
   ✅ "Admin tarafından onaylanmayı beklemektedir" mesajı
```

### **TEST 2: Email Doğrulama Başarısız**
```
1. Kayıt Formuna Gir
   ✅ Form Valid
   ✅ User Oluştur
   ✅ Email GÖNDERME HATASI
   ❌ User.delete() (Silinir)
   ❌ "Email gönderilemedi" hata mesajı
   ✅ Kayıt sayfasında kal
```

### **TEST 3: Admin Onayı**
```
1. Admin Paneli
   ✅ Profil listesine gir
   ✅ Pasif öğrencileri filtrele
   ✅ "Aktif Öğrenci Yap" action tıkla
   ✅ Profil.status = aktif_ogrenci
   ✅ User.is_active = True YAPILMALI (Admin sonra yapmalı!)
```

---

## **PHASE 8: Admin'de User.is_active'i de Enable Et**

### ✅ KOD (Admin User Panel'de):
```python
# Django'nun varsayılan UserAdmin'i extend et

from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib import admin

class CustomUserAdmin(DjangoUserAdmin):
    list_display = DjangoUserAdmin.list_display + ('is_active_display',)
    list_filter = DjangoUserAdmin.list_filter + ('is_active',)
    
    fieldsets = DjangoUserAdmin.fieldsets + (
        ('Hesap Durumu', {
            'fields': ('is_active',),
            'description': '⚠️ is_active=True yapıldığı zaman hesap aktif hale gelir.'
        }),
    )
    
    def is_active_display(self, obj):
        if obj.is_active:
            return format_html('✅ Aktif')
        return format_html('❌ Pasif')
    is_active_display.short_description = "Hesap Durumu"

# Django'nun varsayılan UserAdmin'i kaldırıp yenisini ekle
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
```

---

## **ÖZET TABLO**

| Durum | User.is_active | Profil.status | Profil.email_dogrulandi | Login Yapabilir mi? |
|------|--------|--------|--------|--------|
| Kayıt Yapılırken | ❌ False | pasif_ogrenci | False | ❌ NO |
| Email Doğrulama Başarılı | ❌ False | pasif_ogrenci | ✅ True | ❌ NO |
| Admin Onay Verirse | ✅ True | aktif_ogrenci | ✅ True | ✅ YES |
| Admin İptal Ederse | ❌ False | iptal | ✅ True | ❌ NO |

---

## **UYARILACAK MESAJLAR**

```
❌ Doğrulama Sırasında:
   - "❌ Email gönderilemedi. Lütfen yöneticiye başvurun."
   - "❌ Oturum süresi dolmuş. Lütfen tekrar kayıt olun."
   - "❌ Hatalı doğrulama kodu."

✅ Doğrulama Sonrası:
   - "🎉 Email doğrulandı! Admin tarafından onaylanmayı beklemektedir."

⏳ Giriş Sırasında:
   - "❌ Email adresiniz henüz doğrulanmamıştır."
   - "⏳ Email adresiniz doğrulandı! Ancak admin tarafından onaylanmayı beklemektedir."
   - "🚫 Hesabınız yönetici tarafından iptal edilmiştir."
```

---

**HAZIR! Adım adım uygulamaya başlayabiliriz.** ✅
