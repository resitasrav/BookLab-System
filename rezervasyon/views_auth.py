# Bu dosya views.py dosyasindan ayrildi.
# TURKCE ARAMA ANAHTARLARI: view, sayfa, islem, BookLab

import json
import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_encode, url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import (
    KullaniciGuncellemeFormu,
    ProfilGuncellemeFormu,
    ArizaFormu,
    KayitFormu,
    EmailOrUsernameAuthenticationForm,
)
from .models import Laboratuvar, Cihaz, Randevu, Profil, Duyuru, Ariza
from .utils import render_to_pdf
from .view_helpers import (
    EMAIL_DOGRULAMA_KOD_SURESI_DAKIKA,
    IPTAL_MIN_SURE_SAAT,
    dogrulama_kodu_uret,
    kod_suresi_doldu_mu,
    dogrulama_maili_gonder,
    check_overlap,
)

logger = logging.getLogger(__name__)

# TURKCE ARAMA: giris, kayit, email dogrulama, sifre sifirlama, kod tekrar gonderme
class CustomLoginView(auth_views.LoginView):
    template_name = "giris.html"
    form_class = EmailOrUsernameAuthenticationForm

def kayit(request):
    if request.method == "POST":
        form = KayitFormu(request.POST)
        if form.is_valid():
            # BUG-1 DÜZELTİLDİ: Tüm alanlar session'a yazılıyor
            user_data = {
                'username':   form.cleaned_data['username'],
                'email':      form.cleaned_data['email'],
                'password':   form.cleaned_data['password'],
                'first_name': form.cleaned_data.get('first_name', ''),
                'last_name':  form.cleaned_data.get('last_name', ''),
                'telefon':    form.cleaned_data.get('telefon', ''),
            }

            dogrulama_kodu = dogrulama_kodu_uret()

            request.session['temp_user_data'] = user_data
            request.session['dogrulama_kodu'] = dogrulama_kodu
            request.session['kod_olusturma_tarihi'] = timezone.now().isoformat()

            try:
                dogrulama_maili_gonder(user_data["email"], dogrulama_kodu, user_data.get("first_name", ""))
                messages.success(request, "✅ Doğrulama kodu e-posta adresinize gönderildi.")
                return redirect("email_dogrulama")
            except Exception:
                messages.error(request, "❌ E-posta gönderiminde hata oluştu. Lütfen tekrar deneyin.")
    else:
        form = KayitFormu()
    return render(request, "kayit.html", {"form": form})

def email_dogrulama(request):
    # Session verilerini çek
    user_data = request.session.get('temp_user_data')
    dogrulama_kodu = request.session.get('dogrulama_kodu')
    olusturma_str = request.session.get('kod_olusturma_tarihi')

    if not user_data or not dogrulama_kodu:
        messages.error(request, "❌ Geçersiz oturum. Lütfen yeniden kayıt olun.")
        return redirect("kayit")

    if request.method == "POST":
        girilen_kod = request.POST.get("kod", "").strip()
        olusturma_tarihi = parse_datetime(olusturma_str)
        
        # ⏳ 1 DAKİKALIK SÜRE KONTROLÜ
        if kod_suresi_doldu_mu(olusturma_str):
            for key in ("temp_user_data", "dogrulama_kodu", "kod_olusturma_tarihi"):
                request.session.pop(key, None)
            messages.error(request, "⏳ Süre doldu. Kayıt işleminiz iptal edildi, lütfen tekrar başlayın.")
            return redirect("kayit")

        # ✅ KOD DOĞRUYSA: VERİTABANINA YAZIYORUZ
        if girilen_kod == dogrulama_kodu:
            # 1. Kullanıcıyı tüm alanlarla oluştur (BUG-1 DÜZELTİLDİ)
            user = User.objects.create_user(
                username=user_data['username'],
                email=user_data['email'],
                password=user_data['password'],
                first_name=user_data.get('first_name', ''),
                last_name=user_data.get('last_name', ''),
                is_active=False  # Admin onayı bekleniyor
            )

            # 2. Profil Ayarlarını Güncelle (BUG-2 DÜZELTİLDİ: 'pasif_kullanici')
            profil = user.profil
            profil.status = 'pasif_kullanici'
            profil.telefon = user_data.get('telefon', '')
            profil.email_dogrulandi = True
            profil.email_dogrulama_tarihi = timezone.now()
            profil.save()

            # 3. Session'ı temizle
            for key in ("temp_user_data", "dogrulama_kodu", "kod_olusturma_tarihi"):
                request.session.pop(key, None)

            messages.success(request, "🎉 E-posta doğrulandı! Hesabınız yönetici onayından sonra aktif olacaktır.")
            return redirect("giris")
        else:
            messages.error(request, "❌ Hatalı doğrulama kodu. Lütfen tekrar deneyin.")

    return render(request, "email_dogrulama.html", {
        "baslik": "Hesabınızı Doğrulayın",
        "aciklama": "E-posta adresinize gönderilen kodu girerek kaydınızı tamamlayın.",
        "kod_suresi_saniye": EMAIL_DOGRULAMA_KOD_SURESI_DAKIKA * 60,
    })

def sifre_sifirla_talep(request):
    if request.method == "POST":
        email = request.POST.get('email')
        user = User.objects.filter(email=email).first()
        
        if user:
            # Token ve ID oluşturma
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            protocol = 'https' if request.is_secure() else 'http'
            domain = request.get_host()
            
            
            # 1. HTML İçeriği Hazırla
            # Şablonun içindeki {% url %} etiketinin hata vermemesi için uid ve token'ı AYRI gönderiyoruz.
            html_content = render_to_string(
                "password_reset_email.html", 
                {
                    'user': user,
                    'protocol': protocol,
                    'domain': domain,
                    'uid': uid,    # Şablon bunu 'uid' olarak bekliyor
                    'token': token # Şablon bunu 'token' olarak bekliyor
                }
            )

            # 2. Düz Metin Halini Oluştur
            text_content = strip_tags(html_content)

            # 3. E-posta Nesnesini Oluştur
            email_obj = EmailMultiAlternatives(
                subject="Booklab Laboratuvar Rezervasyon Sistemi | Şifre Sıfırlama",
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )

            # 4. HTML Versiyonunu Ekle ve Gönder
            email_obj.attach_alternative(html_content, "text/html")
            email_obj.send()
            

            messages.success(request, "✅ Şifre sıfırlama bağlantısı e-posta adresinize gönderildi.")
            return render(request, "password_reset_flow.html", {"stage": "done"})
        else:
            messages.error(request, "❌ Bu e-posta adresiyle kayıtlı bir kullanıcı bulunamadı.")
            
    return render(request, "password_reset_flow.html", {"stage": "form"})

def kod_tekrar_gonder(request):
    pending_email_change = request.session.get("pending_email_change")
    if pending_email_change:
        yeni_kod = dogrulama_kodu_uret()
        pending_email_change["kod"] = yeni_kod
        pending_email_change["olusturma"] = timezone.now().isoformat()
        request.session["pending_email_change"] = pending_email_change
        try:
            dogrulama_maili_gonder(
                pending_email_change["email"],
                yeni_kod,
                request.user.get_full_name() or request.user.username,
            )
            messages.success(request, "Yeni doğrulama kodu e-posta adresinize gönderildi.")
        except Exception:
            messages.error(request, "Kod gönderilirken bir hata oluştu.")
        return redirect("email_degisim_dogrulama")

    user_data = request.session.get("temp_user_data")
    if not user_data:
        messages.error(request, "Oturum süresi dolmuş, lütfen tekrar kayıt olun.")
        return redirect("kayit")

    yeni_kod = dogrulama_kodu_uret()
    request.session["dogrulama_kodu"] = yeni_kod
    request.session["kod_olusturma_tarihi"] = timezone.now().isoformat()

    try:
        dogrulama_maili_gonder(user_data["email"], yeni_kod, user_data.get("first_name", ""))
        messages.success(request, "Yeni doğrulama kodu e-posta adresinize gönderildi.")
    except Exception:
        messages.error(request, "Kod gönderilirken bir hata oluştu.")

    return redirect("email_dogrulama")


# NOT: cihaz_durum_degistir'in tek tanımı satır ~588'de bulunuyor.
# BUG-5 DÜZELTİLDİ: Çift tanımlı eski fonksiyon kaldırıldı.
