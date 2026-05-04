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

# TURKCE ARAMA: randevu alma, randevularim, iptal, pdf rapor
@login_required
def randevu_al(request, cihaz_id):
    secilen_cihaz = get_object_or_404(Cihaz, id=cihaz_id)
    simdi = timezone.now()

    secilen_tarih_str = request.GET.get("tarih")
    try:
        if secilen_tarih_str:
            secilen_tarih = datetime.strptime(secilen_tarih_str, "%Y-%m-%d").date()
        else:
            secilen_tarih = simdi.date()
    except ValueError:
        secilen_tarih = simdi.date()
    
    if not secilen_cihaz.aktif_mi:
        messages.error(request, f"⛔ '{secilen_cihaz.isim}' bakımda.")
        return redirect("lab_detay", lab_id=secilen_cihaz.lab.id)

    # Tarih belirleme 
    secilen_tarih_str = request.GET.get("tarih")
    try:
        secilen_tarih = datetime.strptime(secilen_tarih_str, "%Y-%m-%d").date() if secilen_tarih_str else timezone.now().date()
    except ValueError:
        secilen_tarih = timezone.now().date()

    if request.method == "POST":
        try:
            t_obj = datetime.strptime(request.POST.get("tarih"), "%Y-%m-%d").date()
            b_saat_ham = datetime.strptime(request.POST.get("baslangic"), "%H:%M")
            bit_saat_ham = datetime.strptime(request.POST.get("bitis"), "%H:%M")

            #  SAAT YUVARLAMA MANTIĞI ---
            def yuvarla(dt):
                dakika = dt.minute
                
                # En yakın 10'a yuvarla
                yuvarlanmis = round(dakika / 10) * 10

                if yuvarlanmis == 60:
                    # Bir sonraki saate geç
                    return (dt + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
                else:
                    return dt.replace(minute=yuvarlanmis, second=0, microsecond=0)

            b_saat_yuvarlak = yuvarla(b_saat_ham).time()
            bit_saat_yuvarlak = yuvarla(bit_saat_ham).time()

            # Değişkenleri güncelle
            b_obj = b_saat_yuvarlak
            bit_obj = bit_saat_yuvarlak
            secilen_tarih = t_obj

        except Exception:
            messages.error(request, "⚠️ Geçersiz tarih/saat formatı.")
            return redirect("randevu_al", cihaz_id=cihaz_id)

        # Zaman Nesnelerini Hazırla
        simdi = timezone.now()
        baslangic_dt = timezone.make_aware(datetime.combine(t_obj, b_obj))
        bitis_dt = timezone.make_aware(datetime.combine(t_obj, bit_obj))
        
        # 1. KURAL: Geçmişe Randevu Engeli
        if baslangic_dt < simdi:
            messages.error(request, "❌ Geçmiş bir zamana randevu alamazsınız.")
            return redirect("randevu_al", cihaz_id=cihaz_id)

        # 2. KURAL: IPTAL_MIN_SURE_SAAT Kontrolü
        limit_vakti = simdi + timedelta(hours=settings.IPTAL_MIN_SURE_SAAT)
        if baslangic_dt < limit_vakti:
            messages.error(request, f"⚠️ Randevu en geç {settings.IPTAL_MIN_SURE_SAAT} saat önceden alınmalıdır.")
            return redirect("randevu_al", cihaz_id=cihaz_id)

        #  SÜRE KISITLAMALARI ---
        fark = (bitis_dt - baslangic_dt).total_seconds() / 3600

        # Min 1 Saat Kontrolü
        if fark < 0.1:
            messages.error(request, "⚠️ En az 10 dakikalık randevu almalısınız. (Saatler otomatik yuvarlanmıştır)")
            return redirect("randevu_al", cihaz_id=cihaz_id)

        # Max 3 Saat Kontrolü (settings.MAX_RANDEVU_SAATI kullanıldı)
        if fark > settings.MAX_RANDEVU_SAATI:
            messages.error(request, f"⚠️ En fazla {settings.MAX_RANDEVU_SAATI} saatlik randevu alabilirsiniz.")
            return redirect("randevu_al", cihaz_id=cihaz_id)

        if fark <= 0:
            messages.error(request, "⚠️ Bitiş saati başlangıçtan sonra olmalıdır.")
            return redirect("randevu_al", cihaz_id=cihaz_id)
        
        # Çakışma Kontrolü ve Kayıt
        with transaction.atomic():
            # 1. Kontrol: Cihaz bazlı çakışma (Mevcut check_overlap fonksiyonun)
            cihaz_cakisiyor = check_overlap(secilen_cihaz, t_obj, b_obj, bit_obj)
            """
            # 2. Kontrol: Kullanıcı bazlı çakışma (Kullanıcı başka bir cihazda mı?)
            # Sadece onay bekleyen veya onaylanan randevulara bakar, iptalleri saymaz.
            kullanici_cakisiyor = Randevu.objects.filter(
                kullanici=request.user,
                tarih=t_obj,
                durum__in=['onay_bekleniyor', 'onaylandi'],
                baslangic_saati__lt=bit_obj, # Başlangıç saati bitişten önceyse
                bitis_saati__gt=b_obj        # Bitiş saati başlangıçtan sonraysa
            ).exists()
            """

            if cihaz_cakisiyor:
                messages.error(request, "⚠️ Bu saat aralığı DOLU veya yuvarlanan saatler çakışmaya neden oldu!")
            
            #elif kullanici_cakisiyor:
            #    messages.error(request, "⚠️ Aynı zaman diliminde başka bir laboratuvar/cihaz için zaten bir randevunuz bulunuyor!")
            else:
                # Her iki kontrol de geçerliyse kaydı yap
                Randevu.objects.create(
                    kullanici=request.user, 
                    cihaz=secilen_cihaz, 
                    tarih=t_obj, 
                    baslangic_saati=b_obj, 
                    bitis_saati=bit_obj
                )
                messages.success(request, f"✅ Randevu {b_obj.strftime('%H:%M')} - {bit_obj.strftime('%H:%M')} arasına oluşturuldu.")
                return redirect("randevularim")

    # Mevcut randevuları listele (Sadece Onay Bekleyen ve Onaylanmış olanlar)
    mevcut_randevular = Randevu.objects.filter(
        cihaz=secilen_cihaz, 
        tarih=secilen_tarih,
        durum__in=['onay_bekleniyor', 'onaylandi'] 
    ).order_by("baslangic_saati")

    return render(request, "randevu_form.html", {
        "cihaz": secilen_cihaz, 
        "secilen_tarih": secilen_tarih.strftime("%Y-%m-%d"), 
        "bugun_tarih": simdi.strftime("%Y-%m-%d"),
        "mevcut_randevular": mevcut_randevular
    })

@login_required
def randevularim(request):
    # Tüm randevuları çekiyoruz
    tum = Randevu.objects.filter(kullanici=request.user).order_by("tarih", "baslangic_saati")
    simdi = datetime.now()

    # AKTİF RANDEVULAR:
    # 1. Zamanı henüz geçmemiş olmalı
    # 2. Durumu 'Onay Bekliyor' veya 'Onaylandı' olmalı (Reddedilenler veya iptaller burada görünmemeli)
    aktif = [
        r for r in tum 
        if datetime.combine(r.tarih, r.baslangic_saati) >= simdi 
        and r.durum in ['onay_bekleniyor', 'onaylandi']
    ]

    # GEÇMİŞ / PASİF RANDEVULAR:
    # 1. Zamanı geçmiş olanlar VEYA 
    # 2. Reddedilmiş/İptal edilmiş olanlar (Zamanı gelecek olsa bile pasif sayılırlar)
    gecmis = [
        r for r in tum 
        if datetime.combine(r.tarih, r.baslangic_saati) < simdi 
        or r.durum in ['reddedildi', 'iptal_edildi']
    ]

    return render(request, "randevularim.html", {
        "aktif_randevular": aktif, 
        "gecmis_randevular": reversed(gecmis)
    })

@login_required
def randevu_pdf_indir(request):
    randevular = (
        Randevu.objects
        .filter(kullanici=request.user)
        .order_by("tarih", "baslangic_saati")
    )

    context = {
        "user": request.user,
        "randevular": randevular,
    }

    filename = f"randevular_{request.user.username}.pdf"

    return render_to_pdf(
        "randevu_pdf.html", 
        context, 
        filename
    )

@login_required
@require_POST
def randevu_iptal(request, randevu_id):
    # Randevuyu bul, eğer kullanıcıya ait değilse 404 döndür
    randevu = get_object_or_404(Randevu, id=randevu_id, kullanici=request.user)
    
    # --- YENİ ÖZELLİK: İPTAL SÜRESİ KONTROLÜ ---
    simdi = timezone.now()
    # Randevu başlangıç zamanını oluşturuyoruz
    randevu_vakti = timezone.make_aware(datetime.combine(randevu.tarih, randevu.baslangic_saati))
    
    # Sabite göre minimum iptal süresi kontrolü (Örn: 1 saat kala iptal engeli)
    limit_vakti = simdi + timedelta(hours=settings.IPTAL_MIN_SURE_SAAT)
    
    if randevu_vakti < limit_vakti:
        messages.error(request, f"❌ Randevuya {settings.IPTAL_MIN_SURE_SAAT} saatten az kaldığı için artık iptal edemezsiniz.")
        return redirect("randevularim")
    # --- KONTROL BİTİŞ ---

    # Sadece 'Onay Bekliyor' veya 'Onaylandı' durumundaki randevular iptal edilebilir
    if randevu.durum in ['onay_bekleniyor', 'onaylandi']:
        randevu.durum = 'iptal_edildi'
        randevu.save()
        messages.success(request, "✅ Randevunuz başarıyla iptal edildi.")
    else:
        messages.error(request, "Bu randevu şu anki durumu nedeniyle iptal edilemez.")
        
    return redirect("randevularim")
