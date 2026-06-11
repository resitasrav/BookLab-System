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
from django.core.cache import cache
from django.core.paginator import Paginator
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
from django.db.models import Count as _Count

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
    SLOT_DAKIKA,
    dogrulama_kodu_uret,
    kod_suresi_doldu_mu,
    dogrulama_maili_gonder,
    check_overlap,
    otomatik_geldi_isaretle,
)
from django.urls import reverse

logger = logging.getLogger(__name__)

# TURKCE ARAMA: yonetim paneli, admin islemleri, ariza, toplu islem
@staff_member_required
def onay_bekleyen_sayisi(request):
    """
    Sol menüdeki bildirimleri (badge) ait oldukları sekmelere dağıtır.
    Pasif öğrenciler ve Bekleyen randevular artık ayrı sayılır.
    """
    # Bu uçnokta sol menüdeki badge'ler için sık (polling) çağrılır.
    # Sayaçlar global olduğundan 30 sn'lik kısa cache RAM/CPU yükünü azaltır.
    veri = cache.get("badge_sayaclari")
    if veri is None:
        veri = {
            "pasif_ogrenci": User.objects.filter(is_active=False).count(),
            "bekleyen_randevu": Randevu.objects.filter(durum='onay_bekleniyor').count(),
            "acik_ariza": Ariza.objects.filter(cozuldu_mu=False).count(),
        }
        cache.set("badge_sayaclari", veri, 30)
    return JsonResponse(veri)


@staff_member_required
def egitmen_paneli(request):
    # 48 saat geçmiş onaylı randevuları otomatik "geldi" yap (lazy senkron)
    otomatik_geldi_isaretle()

    # AY BASLı FİLTRELEME - varsayılan olarak şu anki ayı gösterir
    ay_ara = request.GET.get('ay_ara')
    if ay_ara is None:
        ay_ara = timezone.now().strftime('%Y-%m')
    
    # Ay filtresini önce çöz— lab grafiği de aynı filtreyi kullanabilsin
    yil = ay = None
    if ay_ara:
        try:
            yil, ay = ay_ara.split('-')
        except ValueError:
            pass

    # Lab grafiği: seçili aya göre filtreli randevu sayısı
    if yil and ay:
        labs = Laboratuvar.objects.annotate(
            randevu_sayisi=_Count(
                'cihaz__randevu',
                filter=Q(cihaz__randevu__tarih__year=yil, cihaz__randevu__tarih__month=ay)
            )
        )
    else:
        labs = Laboratuvar.objects.annotate(randevu_sayisi=_Count('cihaz__randevu'))

    # Tüm randevular (ay filtreli sayım için)
    tum_randevular = Randevu.objects.all()

    # Yaklaşan randevular: bugün ve sonrası, onaylı/işlem bekleyen randevular.
    # Otomatik onay nedeniyle bunlar genelde "onaylandı" durumundadır; yönetici
    # buradan geldi/gelmedi/iptal işlemlerini yapabilir. (Ay filtresinden bağımsız.)
    bugun = timezone.now().date()
    yaklasan_randevular_qs = Randevu.objects.filter(
        durum__in=[Randevu.ONAY_BEKLENIYOR, Randevu.ONAYLANDI],
        tarih__gte=bugun,
    ).order_by("tarih", "baslangic_saati")

    # Ay filtrelemesini yalnızca özet sayıma uygula
    if yil and ay:
        tum_randevular = tum_randevular.filter(tarih__year=yil, tarih__month=ay)

    # --- EN AKTİF KULLANICILAR (En Çok Kullanılan Lab Bazında — Top 10) ---
    top_users_of_top_lab = []
    top_lab_name = None
    try:
        ay_randevular = Randevu.objects.all()
        if yil and ay:
            ay_randevular = ay_randevular.filter(tarih__year=yil, tarih__month=ay)

        # 1. En çok kullanılan labı bul (cihaz üzerinden lab'a ulaş)
        top_lab_entry = (
            ay_randevular
            .values('cihaz__lab_id')
            .annotate(lab_count=_Count('id'))
            .order_by('-lab_count')
            .first()
        )

        if top_lab_entry:
            top_lab_id = top_lab_entry['cihaz__lab_id']
            lab_obj = Laboratuvar.objects.get(pk=top_lab_id)
            top_lab_name = lab_obj.isim

            # 2. O labdaki tüm kullanıcıları randevu sayısına göre sırala (Top 10)
            user_entries = (
                ay_randevular
                .filter(cihaz__lab_id=top_lab_id)
                .values('kullanici_id')
                .annotate(booking_count=_Count('id'))
                .order_by('-booking_count')[:10]
            )

            # User nesnelerini tek sorguda çek
            user_ids = [e['kullanici_id'] for e in user_entries]
            users_map = {u.pk: u for u in User.objects.filter(pk__in=user_ids)}

            for entry in user_entries:
                u = users_map.get(entry['kullanici_id'])
                if u:
                    top_users_of_top_lab.append({
                        'id': u.pk,
                        'name': u.get_full_name() or u.username,
                        'email': u.email,
                        'booking_count': entry['booking_count'],
                    })
    except Exception:
        pass

    context = {
        "toplam_randevu": tum_randevular.count(),
        "yaklasan_sayisi": yaklasan_randevular_qs.count(),
        "yaklasan_randevular": yaklasan_randevular_qs[:8],
        "arizali_cihazlar": Cihaz.objects.filter(aktif_mi=False).count(),
        "toplam_kullanici": User.objects.filter(is_active=True).count(),
        "lab_isimleri": list(labs.values_list('isim', flat=True)),
        "randevu_sayilari": [lab.randevu_sayisi for lab in labs],
        "search_ay": ay_ara,
        "top_users_of_top_lab": top_users_of_top_lab,
        "top_lab_name": top_lab_name,
    }
    return render(request, "yonetim_paneli.html", context)

# ============================================================
# GÜNLÜK YOKLAMA EKRANI  (MODÜLER — KOLAYCA KALDIRILABİLİR)
# Kaldırmak için: bu view + urls.py'deki "gunluk_yoklama" path'i +
# templates/egitmen_paneli.html + base.html'deki Yoklama nav linkini silmek yeterli.
# ============================================================
@staff_member_required
def gunluk_yoklama(request):
    """Bugünün randevularını saat sırasına göre listeleyen yoklama ekranı."""
    bugun = timezone.now().date()
    randevular = (
        Randevu.objects
        .filter(tarih=bugun)
        .select_related("kullanici", "cihaz__lab")
        .order_by("baslangic_saati")
    )
    return render(request, "egitmen_paneli.html", {
        "randevular": randevular,
        "bugun": bugun,
    })


# ============================================================
# TOPLU RANDEVU OLUŞTURMA  (10 dk slot ızgarası)
# ============================================================
@login_required
def toplu_randevu(request):
    """Çoklu 10 dk slot seçerek toplu randevu oluşturma.

    - Yönetici: cihaz + tarih + KULLANICI seçer, herhangi biri adına oluşturur.
    - Normal kullanıcı: cihaz + tarih seçer, randevular DAİMA KENDİ adına oluşur
      (gönderilen kullanıcı parametresi yok sayılır — başkası adına alamaz).
    Oluşturulan randevular doğrudan ONAYLANDI durumundadır.
    """
    yonetici_mi = request.user.is_staff
    cihazlar = Cihaz.objects.filter(aktif_mi=True).select_related('lab').order_by('lab__isim', 'isim')
    # Kullanıcı listesini yalnızca yöneticiye yükle (gereksiz veri çekme).
    kullanicilar = User.objects.filter(is_active=True).order_by('first_name', 'username') if yonetici_mi else []

    secili_cihaz_id = request.POST.get('cihaz') or request.GET.get('cihaz') or ''
    # Normal kullanıcıda hedef her zaman kendisidir.
    if yonetici_mi:
        secili_kullanici_id = request.POST.get('kullanici') or request.GET.get('kullanici') or ''
    else:
        secili_kullanici_id = str(request.user.id)
    tarih_str = request.POST.get('tarih') or request.GET.get('tarih') or ''

    bugun = timezone.now().date()
    try:
        secili_tarih = datetime.strptime(tarih_str, "%Y-%m-%d").date() if tarih_str else bugun
    except ValueError:
        secili_tarih = bugun

    secili_cihaz = Cihaz.objects.filter(id=secili_cihaz_id).first() if secili_cihaz_id else None

    # --- POST: seçili slotlardan randevuları oluştur ---
    if request.method == 'POST' and secili_cihaz:
        # Hedef kullanıcı: yönetici seçer, normal kullanıcı her zaman kendisidir.
        if yonetici_mi:
            if not secili_kullanici_id:
                messages.error(request, "⚠️ Lütfen randevu sahibi bir kullanıcı seçin.")
                return redirect(f"{reverse('toplu_randevu')}?cihaz={secili_cihaz.id}&tarih={secili_tarih.isoformat()}")
            kullanici = get_object_or_404(User, id=secili_kullanici_id)
        else:
            kullanici = request.user
        # Her aralık "HH:MM-HH:MM" biçiminde gelir: ilk tıklanan slot başlangıç,
        # ikinci tıklanan slotun bitişi de aralığın bitişidir (tek randevu).
        secilen_araliklar = request.POST.getlist('aralik')  # ["09:00-09:30", ...]
        simdi = timezone.now()
        olusturulan = atlanan = 0

        with transaction.atomic():
            for aralik in secilen_araliklar:
                try:
                    bas_str, bit_str = aralik.split('-', 1)
                    b = datetime.strptime(bas_str.strip(), "%H:%M").time()
                    bit = datetime.strptime(bit_str.strip(), "%H:%M").time()
                except (ValueError, AttributeError):
                    continue
                # Bitiş başlangıçtan sonra olmalı ve 10 dk hizalı olmalı
                if bit <= b or b.minute % SLOT_DAKIKA or bit.minute % SLOT_DAKIKA:
                    atlanan += 1
                    continue
                baslangic_dt = timezone.make_aware(datetime.combine(secili_tarih, b))
                # Geçmiş veya çakışan aralıkları atla
                if baslangic_dt < simdi or check_overlap(secili_cihaz, secili_tarih, b, bit):
                    atlanan += 1
                    continue
                Randevu.objects.create(
                    kullanici=kullanici,
                    cihaz=secili_cihaz,
                    tarih=secili_tarih,
                    baslangic_saati=b,
                    bitis_saati=bit,
                    durum=Randevu.ONAYLANDI,
                    onaylayan_admin=request.user,
                )
                olusturulan += 1

        if olusturulan:
            mesaj = f"✅ {olusturulan} randevu oluşturuldu ve onaylandı."
            if atlanan:
                mesaj += f" ({atlanan} aralık dolu/geçmiş/geçersiz olduğu için atlandı.)"
            messages.success(request, mesaj)
        else:
            messages.error(request, "⚠️ Randevu oluşturulamadı: aralık seçilmedi ya da seçilenlerin tamamı dolu/geçmiş.")

        geri = f"{reverse('toplu_randevu')}?cihaz={secili_cihaz.id}&tarih={secili_tarih.isoformat()}&kullanici={secili_kullanici_id}"
        return redirect(geri)

    # --- GET: slot ızgarasını hazırla (cihaz + tarih seçiliyse) ---
    saat_gruplari = []
    if secili_cihaz:
        # O gün için dolu aralıkları tek sorguda çek
        dolu_araliklar = list(
            Randevu.objects.filter(
                cihaz=secili_cihaz,
                tarih=secili_tarih,
                durum__in=[Randevu.ONAY_BEKLENIYOR, Randevu.ONAYLANDI, Randevu.GELDI],
            ).values_list('baslangic_saati', 'bitis_saati')
        )
        simdi = timezone.now()
        gun_basi = datetime.combine(secili_tarih, datetime.min.time())
        gun_sonu = gun_basi + timedelta(days=1)

        cur = gun_basi
        saat_map = {}  # "HH" -> [slot, ...]
        # Son blok 23:50 (bitişi 24:00 olur); "< gun_sonu" ile bunu da dahil ederiz
        # ancak 24:00 bitişi geçersiz olduğundan ızgaranın son bloğunu pasif bırakırız.
        while cur < gun_sonu:
            b = cur.time()
            bitis_dt = cur + timedelta(minutes=SLOT_DAKIKA)
            bit = bitis_dt.time()
            son_blok = bitis_dt >= gun_sonu  # 23:50 → bitişi gün sınırını aşar
            dolu = any(db < bit and de > b for (db, de) in dolu_araliklar) if not son_blok else False
            gecmis = timezone.make_aware(cur) < simdi
            grup = b.strftime('%H')
            saat_map.setdefault(grup, []).append({
                'deger': b.strftime('%H:%M'),
                'mins': b.hour * 60 + b.minute,  # gün başından dakika ofseti
                'pasif': dolu or gecmis or son_blok,
            })
            cur = bitis_dt
        saat_gruplari = [{'saat': k, 'slotlar': v} for k, v in saat_map.items()]

    context = {
        'yonetici_mi': yonetici_mi,
        'cihazlar': cihazlar,
        'kullanicilar': kullanicilar,
        'secili_cihaz': secili_cihaz,
        'secili_cihaz_id': str(secili_cihaz_id),
        'secili_kullanici_id': str(secili_kullanici_id),
        'secili_tarih': secili_tarih.isoformat(),
        'bugun': bugun.isoformat(),
        'saat_gruplari': saat_gruplari,
    }
    return render(request, "toplu_randevu.html", context)


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
    # select_related('user') ile template'teki profil.user.* erişimi N+1 olmaktan çıkar.
    kullanicilar = Profil.objects.select_related('user').order_by('-id')

    # Arama parametresini URL'den yakala (?q=...)
    query = request.GET.get('q', '').strip()

    if query:
        kullanicilar = kullanicilar.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__username__icontains=query)
        ).distinct()

    # Büyük kullanıcı listelerini sayfalara böl (RAM/CPU dostu).
    toplam_kullanici = kullanicilar.count()
    paginator = Paginator(kullanicilar, 25)
    sayfa = paginator.get_page(request.GET.get('sayfa'))

    return render(request, "yonetim_kullanicilar.html", {
        "kullanicilar": sayfa,          # iterasyon + sayfa nesnesi
        "toplam_kullanici": toplam_kullanici,
        "search_q": query  # Arama kutusunda kelimenin kalması için geri gönderiyoruz
    })

@staff_member_required
def arizali_cihaz_listesi(request):
    """
    Tüm cihazları listeler. Arızalı (pasif) olanları en üstte gösterir.
    """
    # aktif_mi False (0) olanlar, True (1) olanlardan önce gelir (order_by yükselen sıra)
    # select_related('lab') ile template'teki cihaz.lab.isim erişimi N+1 olmaktan çıkar.
    cihazlar = Cihaz.objects.select_related('lab').order_by('aktif_mi', 'isim')

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
    # 48 saat geçmiş onaylı randevuları otomatik "geldi" yap (lazy senkron)
    otomatik_geldi_isaretle()

    # select_related ile template'teki kullanici / cihaz / cihaz.lab erişimi
    # N+1 olmaktan çıkar (tek JOIN'li sorgu).
    randevular = (
        Randevu.objects
        .select_related('kullanici', 'cihaz__lab')
        .order_by('-tarih', '-baslangic_saati')
    )

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

    # Büyük randevu listelerini sayfalara böl (RAM/CPU dostu).
    toplam_kayit = randevular.count()
    paginator = Paginator(randevular, 50)
    sayfa = paginator.get_page(request.GET.get('sayfa'))

    context = {
        "randevular":   sayfa,          # iterasyon + sayfa nesnesi
        "toplam_kayit": toplam_kayit,
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
        messages.error(request, "\u274c Geçersiz işlem veya seçim yapılmadı.")
        return redirect('tum_randevular')

    guncellenen = Randevu.objects.filter(id__in=secilen_ids).update(
        durum=gecerli_islemler[islem],
        onaylayan_admin=request.user
    )
    islem_adi = {'onaylandi': 'Onaylandı', 'reddedildi': 'Reddedildi',
                 'geldi': 'Geldi olarak işaretlendi', 'gelmedi': 'Gelmedi olarak işaretlendi'}
    messages.success(request, f"\u2705 {guncellenen} randevu \u2192 {islem_adi[islem]}.")
    return redirect('tum_randevular')


@staff_member_required
def toplu_onay_ajax(request):
    """Dashboard için AJAX toplu onay/red endpoint'i. JSON döner."""
    import json as _json
    if request.method != 'POST':
        return JsonResponse({'error': 'Yalnızca POST kabul edilir.'}, status=405)
    try:
        data = _json.loads(request.body)
        ids   = [int(i) for i in data.get('ids', [])]
        islem = data.get('islem', '')
    except (ValueError, KeyError):
        return JsonResponse({'error': 'Geçersiz veri.'}, status=400)

    gecerli = {'onaylandi', 'reddedildi'}
    if islem not in gecerli or not ids:
        return JsonResponse({'error': 'Geçersiz islem veya boş seçim.'}, status=400)

    with transaction.atomic():
        guncellenen = Randevu.objects.filter(id__in=ids).update(
            durum=islem,
            onaylayan_admin=request.user
        )

    yeni_bekleyen = Randevu.objects.filter(durum=Randevu.ONAY_BEKLENIYOR).count()
    return JsonResponse({'updated': guncellenen, 'yeni_bekleyen': yeni_bekleyen})
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
