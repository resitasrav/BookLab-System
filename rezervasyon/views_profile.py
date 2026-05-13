# Bu dosya views.py dosyasindan ayrildi.
# TURKCE ARAMA ANAHTARLARI: view, sayfa, islem, BookLab

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone

from .forms import KullaniciGuncellemeFormu, ProfilGuncellemeFormu
from .view_helpers import (
    EMAIL_DOGRULAMA_KOD_SURESI_DAKIKA,
    dogrulama_kodu_uret,
    kod_suresi_doldu_mu,
    dogrulama_maili_gonder,
)

logger = logging.getLogger(__name__)

# TURKCE ARAMA: profil duzenle, email degistirme, yeni email dogrulama
@login_required
def profil_duzenle(request):
    if request.method == "POST":
        u_form = KullaniciGuncellemeFormu(request.POST, instance=request.user)
        p_form = ProfilGuncellemeFormu(request.POST, request.FILES, instance=request.user.profil)
        if u_form.is_valid() and p_form.is_valid():
            yeni_email = u_form.cleaned_data.get("email")
            eski_email = request.user.email
            user = u_form.save(commit=False)
            email_degisti = yeni_email and yeni_email.lower() != (eski_email or "").lower()

            if email_degisti:
                user.email = eski_email
                user.save(update_fields=["first_name", "last_name", "email"])
                p_form.save()
                kod = dogrulama_kodu_uret()
                request.session["pending_email_change"] = {
                    "email": yeni_email,
                    "kod": kod,
                    "olusturma": timezone.now().isoformat(),
                }
                try:
                    dogrulama_maili_gonder(yeni_email, kod, request.user.get_full_name() or request.user.username)
                    messages.info(request, "Yeni e-posta adresinize doğrulama kodu gönderildi. Değişiklik kod onayından sonra uygulanacak.")
                    return redirect("email_degisim_dogrulama")
                except Exception:
                    request.session.pop("pending_email_change", None)
                    messages.error(request, "E-posta doğrulama kodu gönderilemedi. Lütfen adresi ve SMTP ayarlarını kontrol edin.")
            else:
                user.save()
                p_form.save()
                messages.success(request, "Profil güncellendi.")
                return redirect("randevularim")
    else:
        u_form = KullaniciGuncellemeFormu(instance=request.user)
        p_form = ProfilGuncellemeFormu(instance=request.user.profil)
    return render(request, "profil_duzenle.html", {"u_form": u_form, "p_form": p_form})



@login_required
def email_degisim_dogrulama(request):
    pending = request.session.get("pending_email_change")
    if not pending:
        messages.error(request, "Bekleyen bir e-posta değişikliği bulunamadı.")
        return redirect("profil_duzenle")

    if request.method == "POST":
        girilen_kod = request.POST.get("kod", "").strip()
        if kod_suresi_doldu_mu(pending.get("olusturma")):
            request.session.pop("pending_email_change", None)
            messages.error(request, "Doğrulama kodunun süresi doldu. Lütfen e-posta değişikliğini tekrar başlatın.")
            return redirect("profil_duzenle")

        if girilen_kod == pending.get("kod"):
            request.user.email = pending["email"]
            request.user.save(update_fields=["email"])
            profil = request.user.profil
            profil.email_dogrulandi = True
            profil.email_dogrulama_tarihi = timezone.now()
            profil.save(update_fields=["email_dogrulandi", "email_dogrulama_tarihi"])
            request.session.pop("pending_email_change", None)
            messages.success(request, "E-posta adresiniz doğrulandı ve güncellendi.")
            return redirect("randevularim")
        messages.error(request, "Hatalı doğrulama kodu. Lütfen tekrar deneyin.")

    return render(request, "email_dogrulama.html", {
        "baslik": "Yeni E-postayı Doğrulayın",
        "aciklama": "E-posta adresinizi değiştirmek için yeni adresinize gönderilen kodu girin.",
        "kod_suresi_saniye": EMAIL_DOGRULAMA_KOD_SURESI_DAKIKA * 60,
    })
