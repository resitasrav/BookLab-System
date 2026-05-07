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

# TURKCE ARAMA: yonetim paneli, admin islemleri, ariza, toplu islem
@staff_member_required
def onay_bekleyen_sayisi(request):
    """
    Sol menüdeki bildirimleri (badge) ait oldukları sekmelere dağıtır.
    Pasif öğrenciler ve Bekleyen randevular artık ayrı sayılır.
    """
    # 1. Onay Bekleyen Pasif Öğrenciler 
    pasif_ogrenci = User.objects.filter(is_active=False).count()
    
    # 2. Onay Bekleyen Randevular 
    bekleyen_randevu = Randevu.objects.filter(durum='onay_bekleniyor').count()
    
    # 3. Çözülmemiş Arıza Bildirimleri
    acik_ariza = Ariza.objects.filter(cozuldu_mu=False).count()
    
    return JsonResponse({
        "pasif_ogrenci": pasif_ogrenci,
        "bekleyen_randevu": bekleyen_randevu,
        "acik_ariza": acik_ariza
    })


@staff_member_required
def egitmen_paneli(request):
    from django.db.models import Count as _Count
    
    # AY BASLı FİLTRELEME - varsayılan olarak şu anki ayı gösterir
    ay_ara = request.GET.get('ay_ara')
    if ay_ara is None:
        ay_ara = timezone.now().strftime('%Y-%m')
    
    labs = Laboratuvar.objects.annotate(randevu_sayisi=_Count('cihaz__randevu'))
    
    # Tüm randevuları ve bekleyen randevuları hazırla
    tum_randevular = Randevu.objects.all()
    bekleyen_randevular_tum = Randevu.objects.filter(
        durum__in=[Randevu.ONAY_BEKLENIYOR, Randevu.ONAYLANDI]
    ).order_by("tarih")
    
    # Ay filtrelemesi uygula
    if ay_ara:
        try:
            yil, ay = ay_ara.split('-')
            tum_randevular = tum_randevular.filter(tarih__year=yil, tarih__month=ay)
            bekleyen_randevular_tum = bekleyen_randevular_tum.filter(tarih__year=yil, tarih__month=ay)
        except ValueError:
            pass
    
    context = {
        "toplam_randevu": tum_randevular.count(),
        "bekleyen_onay": bekleyen_randevular_tum.filter(durum=Randevu.ONAY_BEKLENIYOR).count(),
        "bekleyen_randevular": bekleyen_randevular_tum[:5],  # İlk 5'ini göster
        "arizali_cihazlar": Cihaz.objects.filter(aktif_mi=False).count(),
        "toplam_kullanici": User.objects.filter(is_active=True).count(),
        "lab_isimleri": list(labs.values_list('isim', flat=True)),
        "randevu_sayilari": [lab.randevu_sayisi for lab in labs],
        "search_ay": ay_ara,
    }
    return render(request, "yonetim_paneli.html", context)

@staff_member_required
@require_POST
def durum_guncelle(request, randevu_id, yeni_durum):
    gecerli_durumlar = {key for key, _label in Randevu.DURUM_SECENEKLERI}
    if yeni_durum not in gecerli_durumlar:
        messages.error(request, "Geçersiz randevu durumu.")
        return redirect(request.POST.get("next") or "egitmen_paneli")
    r = get_object_or_404(Randevu, id=randevu_id)
    r.durum = yeni_durum; r.onaylayan_admin = request.user; r.save()
    hedef = request.POST.get("next")
    if hedef and url_has_allowed_host_and_scheme(hedef, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(hedef)
    return redirect("egitmen_paneli")


@login_required
def ariza_bildir(request, cihaz_id):
    """Arıza bildirildiğinde ilgili sayaç otomatik güncellenir."""
    cihaz = get_object_or_404(Cihaz, id=cihaz_id)
    if request.method == "POST":
        form = ArizaFormu(request.POST)
        if form.is_valid():
            ariza = form.save(commit=False); ariza.kullanici = request.user; ariza.cihaz = cihaz; ariza.save()
            messages.warning(request, "⚠️ Arıza bildirimi alındı."); return redirect("lab_detay", lab_id=cihaz.lab.id)
    return render(request, "ariza_bildir.html", {"form": ArizaFormu(), "cihaz": cihaz})

# ============================================================
# KAYIT & E-POSTA DOĞRULAMA
# ============================================================

@staff_member_required
def kullanici_listesi(request):
    # kullanıcılar en son kayıt olandan (ID'ye göre ters) başlayarak alıyoruz
    kullanicilar = Profil.objects.all().order_by('-id')

    # Arama parametresini URL'den yakala (?q=...)
    query = request.GET.get('q', '').strip()

    if query:
        # İsim, soyisim, kullanıcı adı veya okul numarasına göre ara
        kullanicilar = kullanicilar.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__username__icontains=query)
        ).distinct()

    return render(request, "yonetim_kullanicilar.html", {
        "kullanicilar": kullanicilar,
        "search_q": query  # Arama kutusunda kelimenin kalması için geri gönderiyoruz
    })

@staff_member_required
def arizali_cihaz_listesi(request):
    """
    Tüm cihazları listeler. Arızalı (pasif) olanları en üstte gösterir.
    """
    # aktif_mi False (0) olanlar, True (1) olanlardan önce gelir (order_by yükselen sıra)
    cihazlar = Cihaz.objects.all().order_by('aktif_mi', 'isim')
    
    return render(request, "yonetim_arizali_cihazlar.html", {
        "cihazlar": cihazlar
    })

@staff_member_required
@require_POST
def cihaz_durum_degistir(request, cihaz_id):
    """Cihazı aktif/pasif yapar. Pasife alınca arıza kaydı düşer, aktife alınca arızalar çözülür."""
    cihaz = get_object_or_404(Cihaz, id=cihaz_id)

    if cihaz.aktif_mi:
        cihaz.aktif_mi = False
        Ariza.objects.create(
            cihaz=cihaz,
            kullanici=request.user,
            aciklama="Cihaz yönetim paneli üzerinden manuel olarak pasife alındı.",
            cozuldu_mu=False
        )
        messages.warning(request, f"⚠️ {cihaz.isim} pasife alındı ve arıza kaydı oluşturuldu.")
    else:
        cihaz.aktif_mi = True
        cihaz.ariza_set.filter(cozuldu_mu=False).update(cozuldu_mu=True)
        messages.success(request, f"✅ {cihaz.isim} aktif edildi, açık arızalar çözüldü olarak işaretlendi.")

    cihaz.save()
    return redirect('arizali_cihaz_listesi')

@staff_member_required
def tum_randevular(request):
    randevular = Randevu.objects.all().order_by('-tarih', '-baslangic_saati')

    q     = request.GET.get('q', '').strip()
    cihaz = request.GET.get('cihaz', '').strip()
    lab   = request.GET.get('lab', '').strip()
    
    # Ay bazlı filtreleme, varsayılan olarak şu anki ayı gösterir
    ay_ara = request.GET.get('ay_ara')
    if ay_ara is None:
        ay_ara = timezone.now().strftime('%Y-%m')

    if q:
        randevular = randevular.filter(
            Q(kullanici__first_name__icontains=q) |
            Q(kullanici__last_name__icontains=q) |
            Q(kullanici__username__icontains=q)
        )
    if cihaz:
        randevular = randevular.filter(cihaz__isim__icontains=cihaz)
    if lab:
        randevular = randevular.filter(cihaz__lab__isim__icontains=lab)
    
    if ay_ara:
        try:
            yil, ay = ay_ara.split('-')
            randevular = randevular.filter(tarih__year=yil, tarih__month=ay)
        except ValueError:
            pass

    context = {
        "randevular": randevular,
        "search_q":     q,
        "search_cihaz": cihaz,
        "search_lab":   lab,
        "search_ay":    ay_ara,
    }
    return render(request, "tum_randevular.html", context)



@staff_member_required
def toplu_islem(request):
    """Seçilen randevulara toplu durum uygular (onayla / reddet / geldi / gelmedi)."""
    if request.method != 'POST':
        return redirect('tum_randevular')

    secilen_ids = request.POST.getlist('secilen_randevular')
    islem = request.POST.get('islem', '')

    gecerli_islemler = {
        'onaylandi': 'onaylandi',
        'reddedildi': 'reddedildi',
        'geldi': 'geldi',
        'gelmedi': 'gelmedi',
    }

    if islem not in gecerli_islemler or not secilen_ids:
        messages.error(request, "❌ Geçersiz işlem veya seçim yapılmadı.")
        return redirect('tum_randevular')

    guncellenen = Randevu.objects.filter(id__in=secilen_ids).update(
        durum=gecerli_islemler[islem],
        onaylayan_admin=request.user
    )
    islem_adi = {'onaylandi': 'Onaylandı', 'reddedildi': 'Reddedildi',
                 'geldi': 'Geldi olarak işaretlendi', 'gelmedi': 'Gelmedi olarak işaretlendi'}
    messages.success(request, f"✅ {guncellenen} randevu → {islem_adi[islem]}.")
    return redirect('tum_randevular')
@login_required
def ariza_bildir_genel(request):
    if request.method == 'POST':
        aciklama = request.POST.get('aciklama')
        # Sistemde bildirim atanacak bir cihaz bulalım
        cihaz = Cihaz.objects.first() 
        
        if cihaz:
            Ariza.objects.create(
                cihaz=cihaz,
                kullanici=request.user,
                aciklama=f"[GENEL SİSTEM SORUNU]: {aciklama}",
                cozuldu_mu=False
            )
            messages.success(request, "Sorun bildiriminiz yöneticiye iletildi.")
        else:
            messages.error(request, "Sistemde kayıtlı cihaz bulunamadığı için bildirim yapılamadı.")

    # ============================================================
    # GÜVENLİ REDIRECT KONTROLÜ (Open Redirect Koruması)
    # ============================================================
    hedef_url = request.META.get('HTTP_REFERER')

    # Eğer HTTP_REFERER dolu gelmişse, adresin bizim sunucumuzda kaldığını doğrula
    if hedef_url:
        is_safe = url_has_allowed_host_and_scheme(
            url=hedef_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        )
        if is_safe:
            return redirect(hedef_url)
            
    # Eğer referer yoksa, manipüle edilmişse veya dış bir siteyi işaret ediyorsa
    # kullanıcıyı her zaman güvenli bir şekilde ana sayfaya gönder
    return redirect('anasayfa')
# ============================================================
#ŞİFRE SIFIRLAMA GÖRÜNÜMLERİ
# ============================================================#
