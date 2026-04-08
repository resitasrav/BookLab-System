import json
import logging
import random
import string
from datetime import datetime, timedelta
from django.utils.dateparse import parse_datetime
# --- DJANGO IMPORTS ---
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import send_mail, EmailMultiAlternatives 
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Count
from django.db import transaction
from django.urls import reverse 
from django.db.models import Q 
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Cihaz
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
#from .decorators import staff_member_required 
from .models import Cihaz
# --- ŞİFRE SIFIRLAMA İÇİN GEREKLİLER ---
from django.contrib.auth.tokens import default_token_generator 
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.utils.html import strip_tags 

# --- MODELS & FORMS ---
from .models import Laboratuvar, Cihaz, Randevu, Profil, Duyuru, Ariza
from .forms import (
    KullaniciGuncellemeFormu,
    ProfilGuncellemeFormu,
    ArizaFormu,
    KayitFormu,
    EmailOrUsernameAuthenticationForm,
)

# --- UTILS ---
from .utils import render_to_pdf # PDF çıktısı almak için eklendi

logger = logging.getLogger(__name__)

class CustomLoginView(auth_views.LoginView):
    template_name = "giris.html"
    form_class = EmailOrUsernameAuthenticationForm

    def form_invalid(self, form):
        """
        Kullanıcı giriş yapamadığında:
        1. Hesap bulunmuş mu?
        2. Neden aktif değil?
           - Email doğrulanmadı mı?
           - Email doğrulandı ama admin başlamadı mı?
           - Hesap iptal edilmiş mi?
        """
        identifier = self.request.POST.get("username", "").strip()
        durum_mesaji = None
        
        if identifier:
            # Kullanıcıyı username veya email ile ara
            user_qs = User.objects.filter(username__iexact=identifier) | User.objects.filter(email__iexact=identifier)
            user = user_qs.first()
            
            if user and not user.is_active:
                # ✅ Kullanıcı bulundu ama is_active=False
                try:
                    profil = Profil.objects.get(user=user)
                    
                    # 📧 EMAIL DOĞRULANDı MI?
                    if not profil.email_dogrulandi:
                        durum_mesaji = "📧 Email adresiniz henüz doğrulanmamıştır. Lütfen gelen kutuğunuzu kontrol edin."
                    
                    # ✅ EMAIL DOĞRULANDIYSA?
                    elif profil.status == 'pasif_ogrenci' and profil.email_dogrulandi:
                        durum_mesaji = "⏳ Email doğrulandı! Ancak yönetici tarafından onaylanmayı beklemektedir."
                    
                    # ❌ HESAP İPTAL EDİLMİŞ?
                    elif profil.status == 'iptal':
                        durum_mesaji = "❌ Hesabınız yönetici tarafından iptal edilmiştir. Lütfen iletişime geçin."
                    
                except Profil.DoesNotExist:
                    durum_mesaji = "Hesabınızda bir sorun oluştu. Lütfen yöneticinizle iletişime geçin."
        
        context = self.get_context_data(form=form)
        if durum_mesaji:
            context["pasif_mesaj"] = durum_mesaji
        
        return self.render_to_response(context)

# ============================================================
# 1️⃣ AYARLAR & YARDIMCI FONKSİYONLAR
# ============================================================
MAX_RANDEVU_SAATI = getattr(settings, "MAX_RANDEVU_SAATI", 24)
IPTAL_MIN_SURE_SAAT = getattr(settings, "IPTAL_MIN_SURE_SAAT", 0)

def check_overlap(cihaz, tarih, baslangic, bitis, exclude_id=None):
    """Çakışma kontrolü: Aynı saatte başka randevu var mı?"""
    qs = Randevu.objects.filter(
        cihaz=cihaz,
        tarih=tarih,
        durum__in=[Randevu.ONAY_BEKLENIYOR, Randevu.ONAYLANDI, Randevu.GELDI],
        baslangic_saati__lt=bitis,
        bitis_saati__gt=baslangic,
    )
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    return qs.exists()

# ============================================================
# 2️⃣ ANA SAYFA & LABORATUVAR GÖRÜNÜMLERİ
# ============================================================
def anasayfa(request):
    labs = Laboratuvar.objects.all()
    duyurular = Duyuru.objects.filter(aktif_mi=True).order_by("-tarih")
    duyurular = Duyuru.objects.filter(aktif_mi=True).order_by("-tarih")
    
    context = {
        "labs": labs, 
        "duyurular": duyurular,
        "bugun": timezone.now().date() # tarih bazlı filtreleme 
    }

    if request.user.is_authenticated:
        aktif_sorgu = Randevu.objects.filter(
            kullanici=request.user,
            tarih__gte=timezone.now().date(),
            durum__in=[Randevu.ONAYLANDI, Randevu.ONAY_BEKLENIYOR]
        )
        context["aktif_randevu_sayisi"] = aktif_sorgu.count()
        context["siradaki_randevu"] = aktif_sorgu.order_by("tarih", "baslangic_saati").first()

    return render(request, "index.html", context)
@login_required
def lab_detay(request, lab_id):
    secilen_lab = get_object_or_404(Laboratuvar, id=lab_id)
    cihaz_listesi = Cihaz.objects.filter(lab=secilen_lab)
    return render(request, "lab_detay.html", {"lab": secilen_lab, "cihazlar": cihaz_listesi})

# ============================================================
# 3️⃣ TAKVİM SİSTEMİ (FULLCALENDAR API)
# ============================================================
@login_required
def genel_takvim(request):
    """Tüm laboratuvarların ortak takvimi"""
    cihazlar_sorgu = Cihaz.objects.filter(aktif_mi=True).values('id', 'isim', 'lab__isim')
    cihazlar = [{'id': c['id'], 'isim': f"{c['lab__isim']} ➝ {c['isim']}"} for c in cihazlar_sorgu]
    cihazlar_json = json.dumps(cihazlar, cls=DjangoJSONEncoder)
    return render(request, "genel_takvim.html", {"cihazlar_json": cihazlar_json})

@login_required
def tum_events_api(request):
    """
    Genel Takvim API: Geçmiş sonuçlananlar ve Gelecek planlılar.
    Çift ikon ve taşma sorununu önlemek için sadeleştirilmiştir.
    """
    bugun = timezone.now().date()
    randevular = Randevu.objects.all()
    events = []

    color_map = {
        Randevu.ONAYLANDI: "#28a745", Randevu.ONAY_BEKLENIYOR: "#ffc107",
        Randevu.GELDI: "#0d6efd", Randevu.GELMEDI: "#6c757d", Randevu.REDDEDILDI: "#dc3545",
    }

    for r in randevular:
        goster = (r.tarih >= bugun and r.durum in [Randevu.ONAY_BEKLENIYOR, Randevu.ONAYLANDI]) or \
                 (r.tarih < bugun and r.durum in [Randevu.GELDI, Randevu.GELMEDI])

        if goster:
            events.append({
                'id': r.id,  # İŞTE EKSİK OLAN HAYAT KURTARICI SATIR BURASI!
                'title': f"{r.cihaz.isim} • {r.baslangic_saati.strftime('%H:%M')}-{r.bitis_saati.strftime('%H:%M')}",
                'start': f"{r.tarih.isoformat()}T{r.baslangic_saati.strftime('%H:%M:%S')}",
                'end': f"{r.tarih.isoformat()}T{r.bitis_saati.strftime('%H:%M:%S')}",
                'color': color_map.get(r.durum, "#3788d8"),
                'extendedProps': {
                    'lab_adi': r.cihaz.lab.isim,
                    'kullanici': r.kullanici.username,
                    'durum': r.get_durum_display()
                }
            })
    return JsonResponse(events, safe=False)

@login_required
def lab_takvim(request, lab_id):
    lab = get_object_or_404(Laboratuvar, id=lab_id)
    cihazlar = list(Cihaz.objects.filter(lab=lab, aktif_mi=True).values('id', 'isim'))
    return render(request, "lab_takvim.html", {"lab": lab, "cihazlar_json": json.dumps(cihazlar, cls=DjangoJSONEncoder)})

@login_required
def lab_events_api(request, lab_id):
    bugun = timezone.now().date()
    randevular = Randevu.objects.filter(cihaz__lab_id=lab_id)
    events = []
    for r in randevular:
        if (r.tarih >= bugun and r.durum in [Randevu.ONAY_BEKLENIYOR, Randevu.ONAYLANDI]) or \
           (r.tarih < bugun and r.durum in [Randevu.GELDI, Randevu.GELMEDI]):
            events.append({
                'title': f"{r.cihaz.isim} • {r.baslangic_saati.strftime('%H:%M')}-{r.bitis_saati.strftime('%H:%M')}",
                'start': f"{r.tarih.isoformat()}T{r.baslangic_saati.strftime('%H:%M:%S')}",
                'end': f"{r.tarih.isoformat()}T{r.bitis_saati.strftime('%H:%M:%S')}",
                'color': "#28a745" if r.durum == Randevu.ONAYLANDI else "#ffc107",
                'extendedProps': {'kullanici': r.kullanici.username, 'durum': r.get_durum_display()}
            })
    return JsonResponse(events, safe=False)

# ============================================================
# 4️⃣ KULLANICI İŞLEMLERİ (RANDEVU ALMA & PROFİL)
# ============================================================
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
                # Dakikayı al: 0-14 -> 00 | 15-44 -> 30 | 45-59 -> Sonraki Saat :00
                dakika = dt.minute
                if dakika < 15:
                    return dt.replace(minute=0, second=0)
                elif dakika < 45:
                    return dt.replace(minute=30, second=0)
                else:
                    return (dt + timedelta(hours=1)).replace(minute=0, second=0)

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
        if fark < 1:
            messages.error(request, "⚠️ En az 1 saatlik randevu almalısınız. (Saatler otomatik yuvarlanmıştır)")
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

            # 2. Kontrol: Kullanıcı bazlı çakışma (Kullanıcı başka bir cihazda mı?)
            # Sadece onay bekleyen veya onaylanan randevulara bakar, iptalleri saymaz.
            kullanici_cakisiyor = Randevu.objects.filter(
                kullanici=request.user,
                tarih=t_obj,
                durum__in=['onay_bekleniyor', 'onaylandi'],
                baslangic_saati__lt=bit_obj, # Başlangıç saati bitişten önceyse
                bitis_saati__gt=b_obj        # Bitiş saati başlangıçtan sonraysa
            ).exists()

            if cihaz_cakisiyor:
                messages.error(request, "⚠️ Bu saat aralığı DOLU veya yuvarlanan saatler çakışmaya neden oldu!")
            elif kullanici_cakisiyor:
                messages.error(request, "⚠️ Aynı zaman diliminde başka bir laboratuvar/cihaz için zaten bir randevunuz bulunuyor!")
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
def profil_duzenle(request):
    if request.method == "POST":
        u_form = KullaniciGuncellemeFormu(request.POST, instance=request.user)
        p_form = ProfilGuncellemeFormu(request.POST, request.FILES, instance=request.user.profil)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save(); p_form.save()
            messages.success(request, "✅ Profil güncellendi!")
            return redirect("randevularim")
    else:
        u_form = KullaniciGuncellemeFormu(instance=request.user)
        p_form = ProfilGuncellemeFormu(instance=request.user.profil)
    return render(request, "profil_duzenle.html", {"u_form": u_form, "p_form": p_form})

# ============================================================
# 5️⃣ YÖNETİM & BİLDİRİM API 
# ============================================================
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
    context = {
        "toplam_randevu": Randevu.objects.count(),
        "bekleyen_onay": Randevu.objects.filter(durum=Randevu.ONAY_BEKLENIYOR).count(),
        "bekleyen_randevular": Randevu.objects.filter(durum=Randevu.ONAY_BEKLENIYOR).order_by("tarih"),
    }
    return render(request, "yonetim_paneli.html", context)

@staff_member_required
def durum_guncelle(request, randevu_id, yeni_durum):
    r = get_object_or_404(Randevu, id=randevu_id)
    r.durum = yeni_durum; r.onaylayan_admin = request.user; r.save()
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

# Boş kalan fonksiyonlar (URL uyumu için)# rezervasyon/views.py
import random
from django.core.mail import send_mail

def kayit(request):
    if request.method == "POST":
        form = KayitFormu(request.POST)
        if form.is_valid():
          
            user_data = {
                'username': form.cleaned_data['username'],
                'email': form.cleaned_data['email'],
                'password': form.cleaned_data['password'], 

            }
            
            dogrulama_kodu = str(random.randint(100000, 999999))
            
            request.session['temp_user_data'] = user_data
            request.session['dogrulama_kodu'] = dogrulama_kodu
            request.session['kod_olusturma_tarihi'] = timezone.now().isoformat()

            #  Mail Gönderimi
            try:
                send_mail(
                    "BookLab - Kayıt Doğrulama",
                    f"Hoş geldiniz! Doğrulama kodunuz: {dogrulama_kodu}\nSüre: 1 Dakika",
                    settings.DEFAULT_FROM_EMAIL,
                    [user_data['email']],
                    fail_silently=False
                )
                messages.success(request, "Doğrulama kodu gönderildi. Kod girilmeden kaydınız tamamlanmayacaktır.")
                return redirect("email_dogrulama")
            except Exception as e:
                messages.error(request, "E-posta gönderiminde hata oluştu.")
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
        if olusturma_tarihi and timezone.now() > olusturma_tarihi + timedelta(minutes=1):
            request.session.flush() # Oturumu temizle
            messages.error(request, "⏳ Süre doldu. Kayıt işleminiz iptal edildi, lütfen tekrar başlayın.")
            return redirect("kayit")

        # ✅ KOD DOĞRUYSA:  VERİTABANINA YAZIYORUZ
        if girilen_kod == dogrulama_kodu:
            # 1. Kullanıcıyı Şimdi Oluştur
            user = User.objects.create_user(
                username=user_data['username'],
                email=user_data['email'],
                password=user_data['password'],
                is_active=False # Admin onayı için hala pasif
            )
            
            # 2. Profil Ayarlarını Güncelle
            profil = user.profil # post_save sinyali ile oluştuğunu varsayıyoruz
            profil.status = 'pasif_ogrenci'
            profil.email_dogrulandi = True
            profil.email_dogrulama_tarihi = timezone.now()
            profil.save()

            # 3. Güvenlik için session'ı temizler
            request.session.flush()

            messages.success(request, "🎉 E-posta doğrulandı! Hesabınız BookLab yöneticisi tarafından onaylandıktan sonra aktif olacaktır.")
            return redirect("giris")
        else:
            messages.error(request, "❌ Hatalı doğrulama kodu.")

    return render(request, "email_dogrulama.html")
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
            Q(user__username__icontains=query) |
            Q(okul_numarasi__icontains=query)
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
def cihaz_durum_degistir(request, cihaz_id):
    cihaz = get_object_or_404(Cihaz, id=cihaz_id)
    cihaz.aktif_mi = not cihaz.aktif_mi
    
    if cihaz.aktif_mi:
        cihaz.aciklama = "" 
        messages.success(request, f"✅ {cihaz.isim} aktif edildi ve arıza notu temizlendi.")
    else:
        messages.warning(request, f"⚠️ {cihaz.isim} şu an pasif durumda.")
    
    cihaz.save()
    return redirect('arizali_cihaz_listesi')
def tum_randevular(request):
    # Varsayılan Sıralama: En yeni tarihli olan en üstte
    randevular = Randevu.objects.all().order_by('-tarih', '-baslangic_saati')

    # URL'den gelen filtre parametrelerini yakala
    q = request.GET.get('q', '').strip()          # Ad, Soyad veya Kullanıcı Adı
    cihaz = request.GET.get('cihaz', '').strip()  # Cihaz İsmi
    lab = request.GET.get('lab', '').strip()      # Laboratuvar İsmi
    tarih = request.GET.get('tarih_ara', '')      # Belirli Bir Tarih

    # --- FİLTRELEME MANTIĞI ---
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
        
    if tarih:
        randevular = randevular.filter(tarih=tarih)

    context = {
        "randevular": randevular,
        "search_q": q,
        "search_cihaz": cihaz,
        "search_lab": lab,
        "search_tarih": tarih,
    }
    
    return render(request, "tum_randevular.html", context)
@login_required
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

# ============================================================
#yeni doğrulama kodu gonderme
# ============================================================
def kod_tekrar_gonder(request):
    user_id = request.session.get('dogrulama_user_id')
    
    if not user_id:
        messages.error(request, "Oturum süresi dolmuş, lütfen tekrar kayıt olun.")
        return redirect('kayit')

    from django.contrib.auth.models import User
    user = User.objects.get(id=user_id)
    
    # Yeni kod üret ve session'ı güncelle
    yeni_kod = str(random.randint(100000, 999999))
    request.session['dogrulama_kodu'] = yeni_kod
    
    try:
        send_mail(
            "Booklab Laboratuvar Rezervasyon Sistemi | Yeni Doğrulama Kodu",
            f"Merhaba {user.username}, yeni doğrulama kodunuz: {yeni_kod}",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        messages.success(request, "✅ Yeni doğrulama kodu e-posta adresinize gönderildi.")
    except Exception as e:
        messages.error(request, "❌ Kod gönderilirken bir hata oluştu.")

    return redirect('email_dogrulama')


def cihaz_durum_degistir(request, cihaz_id):
    cihaz = get_object_or_404(Cihaz, id=cihaz_id)
    
    if cihaz.aktif_mi:
        # 1. Cihazı pasife al
        cihaz.aktif_mi = False
        
        # 2. ADMIN PANELE OTOMATİK KAYIT DÜŞÜR
        Ariza.objects.create(
            cihaz=cihaz,
            kullanici=request.user, # Yönetici kapattı
            aciklama="Cihaz yönetim paneli üzerinden manuel olarak pasife alındı.",
            cozuldu_mu=False
        )
    else:
        # 1. Cihazı tekrar aktif eder
        cihaz.aktif_mi = True
        
        # 2. ADMIN PANELDEKİ AÇIK ARIZALARI "ÇÖZÜLDÜ" YAPAR
        # Bu cihaza ait çözülmemiş ne kadar arıza varsa hepsini çözüldü olarak işaretler
        cihaz.ariza_set.filter(cozuldu_mu=False).update(cozuldu_mu=True)
        
    cihaz.save()
    return redirect('arizali_cihaz_listesi') 
