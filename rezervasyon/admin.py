# ============================================================
# admin.py – Laboratuvar Randevu Sistemi Yönetim Paneli (V2.1)
# ✅ Mobil Uyumlu | ✅ Belirgin Butonlar | ✅ Geliştirilmiş İşlevler
# ============================================================

import csv
import logging
from django.contrib import admin, messages
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.http import HttpResponse
from django.utils.safestring import mark_safe
from django.shortcuts import redirect, get_object_or_404, render
from urllib.parse import urlparse
from django.urls import path
from django.utils.html import format_html
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.db import models
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.apps import apps
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import AdminMassEmailForm
from .models import (
    Laboratuvar, Cihaz, Randevu, Profil, Ariza, Duyuru,
    OnayBekleyenler, AktifKullanicilar
)

# ============================================================
# LOGGER & ADMIN AYARLARI
# ============================================================
logger = logging.getLogger('admin_operations')

admin.site.site_header = "BookLab Yönetim Paneli"
admin.site.site_title = "BookLab Admin Portal"
admin.site.index_title = "Sistem Kontrol Merkezine Hoş Geldiniz"

# ============================================================
# MOBIL UYUMLU BUTON STİLİ (GLOBAL CSS)
# ============================================================
BUTTON_STYLE_PRIMARY = 'padding:8px 14px; border-radius:6px; color:white; font-weight:600; font-size:12px; text-decoration:none; cursor:pointer; transition:0.2s; display:inline-block; min-width:80px; text-align:center; border:none; box-shadow:0 2px 4px rgba(0,0,0,0.2);'
BUTTON_STYLE_SUCCESS = BUTTON_STYLE_PRIMARY + 'background:#28a745;'
BUTTON_STYLE_DANGER = BUTTON_STYLE_PRIMARY + 'background:#dc3545;'
BUTTON_STYLE_INFO = BUTTON_STYLE_PRIMARY + 'background:#17a2b8;'
BUTTON_STYLE_WARNING = BUTTON_STYLE_PRIMARY + 'background:#ffc107; color:#000;'
BUTTON_STYLE_SECONDARY = BUTTON_STYLE_PRIMARY + 'background:#6c757d;'

# Mobil ekran için responsive wrapper
BUTTON_WRAPPER = 'display:flex; flex-wrap:wrap; gap:6px; align-items:center;'

# ============================================================
# GÜVENLİ REDIRECT
# ============================================================
def safe_redirect(request, fallback="/"):
    """Güvenli redirect - Open Redirect ve CSRF Koruması"""
    referer = request.META.get("HTTP_REFERER")
    
    # Eğer referer (gelinen sayfa) bilgisi yoksa, varsayılan sayfaya yönlendir
    if not referer:
        return redirect(fallback)
        
    # URL'nin gerçekten kendi sunucumuz içinde kalıp kalmadığını kesin olarak denetle
    is_safe = url_has_allowed_host_and_scheme(
        url=referer,
        allowed_hosts={request.get_host()}, # Sadece sitemizin barındığı adrese izin ver
        require_https=request.is_secure(),  # Sitemiz HTTPS ise yönlendirme de HTTPS olmaya zorlanır
    )
    
    if is_safe:
        return redirect(referer)
    else:
        # Eğer URL manipüle edilmişse (dış bir siteye gidiyorsa), güvenli varsayılan sayfaya at
        return redirect(fallback)
# ============================================================
# GLOBAL ACTION FUNCTIONS
# ============================================================

@admin.action(description="📥 Excel (CSV) İndir")
def excel_indir(modeladmin, request, queryset):
    """Seçili satırları CSV olarak dışa aktarır"""
    try:
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="rapor.csv"'
        response.write(u'\ufeff'.encode('utf8'))
        
        writer = csv.writer(response, delimiter=';')
        writer.writerow(["Kullanıcı", "Cihaz", "Tarih", "Saat Aralığı", "Durum"])
        
        for obj in queryset:
            user = getattr(obj, "kullanici", None)
            if user:
                full_name = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip()
                if not full_name:
                    full_name = getattr(user, 'username', '-')
            else:
                full_name = "-"

            writer.writerow([
                full_name,
                getattr(obj, "cihaz", "-"),
                getattr(obj, "tarih", "-"),
                f"{getattr(obj, 'baslangic_saati', '')}-{getattr(obj, 'bitis_saati', '')}",
                obj.get_durum_display() if hasattr(obj, "get_durum_display") else "-"
            ])
        
        logger.info(f"CSV Export: {request.user.username} - {queryset.count()} kayıt")
        return response
    except Exception as e:
        logger.error(f"CSV Export Hatası: {str(e)}")
        return response

@admin.action(description="📧 Bilgilendirme Maili Gönder")
def mail_gonder(modeladmin, request, queryset):
    """Seçili nesnelere bilgilendirme maili gönderi"""
    try:
        sayac = 0
        hatali = 0
        
        for obj in queryset:
            user = obj.kullanici if hasattr(obj, "kullanici") else obj
            
            if not hasattr(user, 'email') or not user.email:
                hatali += 1
                continue
            
            try:
                send_mail(
                    subject="BookLab Sistemi - Bilgilendirme",
                    message="Hesabınızla ilgili önemli bir bildirimi size göndermekteyiz.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                sayac += 1
            except Exception:
                hatali += 1
        
        if sayac > 0:
            modeladmin.message_user(request, f"✅ {sayac} kullanıcıya mail gönderildi.", messages.SUCCESS)
        if hatali > 0:
            modeladmin.message_user(request, f"⚠️ {hatali} hata oluştu.", messages.WARNING)
        
        logger.info(f"Mass Mail: {request.user.username} - {sayac} gönderilen")
    except Exception as e:
        logger.error(f"Mail Gönderme Hatası: {str(e)}")
        modeladmin.message_user(request, "❌ Mail gönderme hatası!", messages.ERROR)

@admin.action(description="📧 Özel Mail Gönder")
def ozel_mail_action(modeladmin, request, queryset):
    """Seçili nesnelere özel mail göndermek için form sayfasına yönlendir"""
    ids = list(queryset.values_list('pk', flat=True))
    request.session['ozel_mail_data'] = {
        'app_label': modeladmin.model._meta.app_label,
        'model': modeladmin.model._meta.model_name,
        'pks': ids,
        'repr': str(modeladmin.model._meta.verbose_name_plural)
    }
    return redirect('admin:rezervasyon_ozel_mail')

@admin.action(description="🔻 Yönetici Yetkisini Geri Al")
def yetkiyi_al(modeladmin, request, queryset):
    """Seçili kullanıcıların yönetici yetkisini geri al (sadece superuser yapabilir)"""
    if not request.user.is_superuser:
        modeladmin.message_user(request, "❌ Bu işlem için yeterli izniniz yok.", messages.ERROR)
        return

    guncellenen = 0
    for obj in queryset:
        user = None
        if isinstance(obj, User):
            user = obj
        elif hasattr(obj, 'user'):
            user = obj.user
        elif hasattr(obj, 'kullanici'):
            user = obj.kullanici

        if user and user != request.user:
            if user.is_staff or user.is_superuser:
                user.is_staff = False
                user.is_superuser = False
                user.save()
                guncellenen += 1

    if guncellenen > 0:
        modeladmin.message_user(request, f"✅ {guncellenen} kullanıcının yönetici yetkisi geri alındı.", messages.SUCCESS)
    else:
        modeladmin.message_user(request, "⚠️ Hiçbir kullanıcı güncellenemedi (kendini indirgeyemezsiniz).", messages.WARNING)


@admin.action(description="🌟 Seçilenleri Yönetici Yap")
def super_kullanici_yap(modeladmin, request, queryset):
    """Seçili kullanıcıları admin yetkisine yükselt"""
    if not request.user.is_superuser:
        modeladmin.message_user(request, "❌ Bu işlem için yeterli izniniz yok.", messages.ERROR)
        return

    guncellenen = 0
    for obj in queryset:
        user = None
        if isinstance(obj, User):
            user = obj
        elif hasattr(obj, 'user'):
            user = obj.user
        elif hasattr(obj, 'kullanici'):
            user = obj.kullanici

        if user and not user.is_superuser:
            user.is_staff = True
            user.is_superuser = True
            user.save()
            guncellenen += 1

    if guncellenen > 0:
        modeladmin.message_user(request, f"✅ {guncellenen} kullanıcı yönetici yapıldı.", messages.SUCCESS)
    else:
        modeladmin.message_user(request, "⚠️ Seçilen kullanıcılar güncellenemedi.", messages.WARNING)

@admin.action(description="🟢 Aktif Yap")
def aktif_yap(modeladmin, request, queryset):
    """Seçili kullanıcıları aktif hale getir"""
    updated = queryset.update(is_active=True)
    modeladmin.message_user(request, f"✅ {updated} kullanıcı aktif yapıldı.", messages.SUCCESS)
    logger.info(f"Aktifleştirme: {request.user.username} - {updated} kayıt")

@admin.action(description="🔴 Pasif Yap")
def pasif_yap(modeladmin, request, queryset):
    """Seçili kullanıcıları pasif hale getir"""
    updated = queryset.update(is_active=False)
    modeladmin.message_user(request, f"🔴 {updated} kullanıcı pasif yapıldı.", messages.WARNING)
    logger.info(f"Pasifleştirme: {request.user.username} - {updated} kayıt")

# ============================================================
# ADMIN MASS MAIL MIXIN (Mail Gönderme Fonksiyonu)
# ============================================================

class AdminMassMailMixin:
    """Kişiselleştirilmiş mail gönderme işlevselliği ekleyen Mixin"""
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('ozel-mail/', self.admin_site.admin_view(self.ozel_mail_view), name='rezervasyon_ozel_mail'),
        ]
        return custom_urls + urls

    def ozel_mail_view(self, request):
        """Özel mail gönderme formu ve işlemesi"""
        data = request.session.get('ozel_mail_data')
        if not data:
            messages.error(request, "❌ Seçilmiş kullanıcı verisi bulunamadı.")
            return redirect('..')

        try:
            Model = apps.get_model(data.get('app_label'), data.get('model'))
            queryset = Model.objects.filter(pk__in=data.get('pks', []))

            recipients = []
            missing_emails = []

            def find_email(o):
                """Nesne içinden email adresini bul"""
                for attr in ('email',):
                    if hasattr(o, attr) and getattr(o, attr):
                        return getattr(o, attr)
                for rel in ('user', 'kullanici', 'owner'):
                    if hasattr(o, rel):
                        try:
                            u = getattr(o, rel)
                            if u and hasattr(u, 'email') and u.email:
                                return u.email
                        except:
                            pass
                if hasattr(o, 'profil'):
                    try:
                        p = getattr(o, 'profil')
                        if p and hasattr(p, 'user') and p.user.email:
                            return p.user.email
                    except:
                        pass
                return None

            seen = set()
            for obj in queryset:
                email = find_email(obj)
                if email:
                    try:
                        validate_email(email)
                        if email.lower() not in seen:
                            seen.add(email.lower())
                            recipients.append((obj, email))
                    except ValidationError:
                        missing_emails.append(obj)
                else:
                    missing_emails.append(obj)

            if request.method == 'POST':
                form = AdminMassEmailForm(request.POST)
                if form.is_valid():
                    subject = form.cleaned_data['subject']
                    message = form.cleaned_data['message']
                    is_html = form.cleaned_data['is_html']

                    sent = 0
                    failed = 0
                    errors = []

                    for _obj, email in recipients:
                        try:
                            if is_html:
                                msg = EmailMultiAlternatives(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
                                msg.attach_alternative(message, "text/html")
                                msg.send()
                            else:
                                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
                            sent += 1
                        except Exception as e:
                            failed += 1
                            errors.append(f"{email}: {str(e)}")

                    try:
                        del request.session['ozel_mail_data']
                    except:
                        pass

                    logger.info(f"Özel Mail: {request.user.username} - {sent} gönderilen")
                    
                    return render(request, 'admin/rezervasyon/ozel_mail_result.html', {
                        'total': len(recipients), 'sent': sent, 'failed': failed,
                        'missing': missing_emails, 'errors': errors
                    })
            else:
                form = AdminMassEmailForm()

            return render(request, 'admin/rezervasyon/ozel_mail_form.html', {
                'form': form,
                'recipient_count': len(recipients),
                'missing_count': len(missing_emails),
                'repr': data.get('repr')
            })
        
        except Exception as e:
            logger.error(f"Özel Mail Hatası: {str(e)}")
            messages.error(request, "❌ Mail işlemi hatası!")
            return redirect('..')

# ============================================================
# LABORATUVAR YÖNETIMI
# ============================================================

@admin.register(Laboratuvar)
class LaboratuvarAdmin(admin.ModelAdmin):
    list_display = ("isim", "cihaz_sayisi", "cihaz_durumu")
    search_fields = ("isim",)
    
    def cihaz_sayisi(self, obj):
        """Laboratuardaki toplam cihaz sayısı"""
        count = obj.cihaz_set.count()
        return format_html(
            '<span style="background:#0056b3; color:white; padding:6px 12px; border-radius:15px; font-weight:600; font-size:12px;">{} cihaz</span>',
            count
        )
    cihaz_sayisi.short_description = "Cihaz Sayısı"
    
    def cihaz_durumu(self, obj):
        """Laboratuardaki cihazların genel durum özeti"""
        aktif = obj.cihaz_set.filter(aktif_mi=True).count()
        pasif = obj.cihaz_set.filter(aktif_mi=False).count()
        
        return format_html(
            '<span style="color:#28a745; font-weight:700; font-size:12px;">✅ {}</span>&nbsp;|&nbsp;<span style="color:#dc3545; font-weight:700; font-size:12px;">🔴 {}</span>',
            aktif, pasif
        )
    cihaz_durumu.short_description = "Durum"

# ============================================================
# CİHAZ YÖNETIMI (GELİŞTİRİLMİŞ & MOBIL UYUMLU)
# ============================================================

@admin.register(Cihaz)
class CihazAdmin(admin.ModelAdmin):
    list_display = ("isim", "lab", "durum", "ariza_notu", "hizli_islem")
    list_filter = ("lab", "aktif_mi")
    search_fields = ("isim", "lab__isim")
    fieldsets = (
        ("Cihaz Bilgileri", {
            'fields': ('isim', 'lab', 'aktif_mi')
        }),
        ("Açıklama & Resim", {
            'fields': ('aciklama', 'resim'),
            'classes': ('collapse',)
        }),
    )

    def ariza_notu(self, obj):
        """Cihazın son zamandaki arıza kaydını gösterir"""
        son_ariza = Ariza.objects.filter(cihaz=obj, cozuldu_mu=False).order_by('-tarih').first()
        if son_ariza:
            text = son_ariza.aciklama[:40] + "..." if len(son_ariza.aciklama) > 40 else son_ariza.aciklama
            return format_html(
                '<span title="{}" style="color:#dc3545; font-weight:600; font-size:11px; cursor:help;">{}</span>',
                son_ariza.aciklama, text
            )
        return mark_safe('<span style="color:#bbb; font-size:11px;">Kayıt Yok</span>')
    ariza_notu.short_description = "Son Arıza"

    def hizli_islem(self, obj):
        """Cihazın durumunu değiştirmek için hızlı buton - MOBIL UYUMLU"""
        if obj.aktif_mi:
            return format_html(
                '<a class="button" href="islem/{}/pasif/" style="{}background:#dc3545;">'
                '  <span style="font-weight:700;">PASIFE AL</span>'
                '</a>',
                obj.id, BUTTON_STYLE_PRIMARY
            )
        else:
            return format_html(
                '<a class="button" href="islem/{}/aktif/" style="{}background:#28a745;">'
                '  <span style="font-weight:700;">✅ AKTİF ET</span>'
                '</a>',
                obj.id, BUTTON_STYLE_PRIMARY
            )
    hizli_islem.short_description = "Durum Değiştir"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('islem/<int:cihaz_id>/<str:durum>/', self.admin_site.admin_view(self.cihaz_durum_guncelle)),
        ]
        return custom_urls + urls

    def cihaz_durum_guncelle(self, request, cihaz_id, durum):
        """Cihaz durumunu aktif/pasif olarak değiştir"""
        try:
            obj = Cihaz.objects.get(pk=cihaz_id)
            
            if durum == "aktif":
                obj.aktif_mi = True
                Ariza.objects.filter(cihaz=obj, cozuldu_mu=False).update(cozuldu_mu=True)
                self.message_user(request, f"✅ {obj.isim} aktif edildi!", messages.SUCCESS)
            else:
                obj.aktif_mi = False
                self.message_user(request, f"🔴 {obj.isim} pasif yapıldı.", messages.WARNING)
            
            obj.save()
            logger.info(f"Cihaz Durum: {obj.isim} → {durum} ({request.user.username})")
        except Exception as e:
            self.message_user(request, f"❌ Hata: {str(e)}", messages.ERROR)
            logger.error(f"Cihaz Durum Hatası: {str(e)}")
        
        return redirect("../../..")

    def durum(self, obj):
        """Cihazın genel durumu (aktif/pasif) - Mevcut kolon için"""
        if not obj.aktif_mi:
            return mark_safe(
                '<span style="color:#dc3545; font-weight:700; font-size:13px;">⚠️ ARIZALI</span>'
            )
        return mark_safe(
            '<span style="color:#28a745; font-weight:700; font-size:13px;">✅ ÇALIŞIYOR</span>'
        )
    durum.short_description = "Statü"

# ============================================================
# RANDEVU YÖNETIMI (GELİŞTİRİLMİŞ & MOBIL UYUMLU)
# ============================================================

@admin.register(Randevu)
class RandevuAdmin(AdminMassMailMixin, admin.ModelAdmin):
    list_display = ("kullanici", "cihaz", "tarih", "saat_araligi", "durum_renkli", "butonlar")
    list_filter = ("durum", "tarih", "cihaz__lab")
    actions = [excel_indir, mail_gonder, ozel_mail_action, super_kullanici_yap]
    search_fields = ("kullanici__username", "cihaz__isim")
    date_hierarchy = "tarih"

    def get_queryset(self, request):
        """Onay bekleyenleri öne almak için queryset'i özelleştir"""
        qs = super().get_queryset(request)
        return qs.order_by(
            models.Case(
                models.When(durum="onay_bekleniyor", then=0),
                default=1,
                output_field=models.IntegerField()
            ), 
            "-tarih"
        )

    def saat_araligi(self, obj):
        """Randevunun saat aralığını göster"""
        return format_html(
            '<span style="color:#0056b3; font-weight:700; font-size:12px;">{} - {}</span>',
            obj.baslangic_saati.strftime("%H:%M"),
            obj.bitis_saati.strftime("%H:%M")
        )
    saat_araligi.short_description = "Saat"

    def durum_renkli(self, obj):
        """Randevunun durumunu rengiyle göster"""
        renk_paleti = {
            "onay_bekleniyor": "#ffc107",
            "onaylandi": "#28a745",
            "geldi": "#17a2b8",
            "gelmedi": "#6c757d",
            "reddedildi": "#dc3545",
            "iptal_edildi": "#495057"
        }
        renk = renk_paleti.get(obj.durum, "#6c757d")
        
        return format_html(
            '<span style="background:{}; color:white; padding:6px 12px; border-radius:20px; font-weight:700; font-size:11px; display:inline-block;">{}</span>',
            renk, obj.get_durum_display()
        )
    durum_renkli.short_description = "Durum"

    def butonlar(self, obj):
        """Randevunun durumuna göre uygun işlem butonları - MOBIL UYUMLU"""
        btn = []
        
        if obj.durum == "onay_bekleniyor":
            btn.append(format_html(
                '<a class="button" href="onayla/{}/" style="{}background:#28a745;">'
                '✅ ONAYLA'
                '</a>',
                obj.id, BUTTON_STYLE_PRIMARY
            ))
            btn.append(format_html(
                '<a class="button" href="iptal/{}/" style="{}background:#dc3545;">'
                '❌ REDDET'
                '</a>',
                obj.id, BUTTON_STYLE_PRIMARY
            ))
        elif obj.durum == "onaylandi":
            btn.append(format_html(
                '<a class="button" href="geldi/{}/" style="{}background:#17a2b8;">'
                '✔ GELDİ'
                '</a>',
                obj.id, BUTTON_STYLE_PRIMARY
            ))
            btn.append(format_html(
                '<a class="button" href="gelmedi/{}/" style="{}background:#6c757d;">'
                '⊗ GELMEDİ'
                '</a>',
                obj.id, BUTTON_STYLE_PRIMARY
            ))
        
        return format_html(
            '<div style="{}">{}</div>',
            BUTTON_WRAPPER, mark_safe(" ".join(btn))
        ) if btn else mark_safe('<span style="color:#bbb;">-</span>')
    butonlar.short_description = "İşlemler"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("onayla/<int:pk>/", self.admin_site.admin_view(self.onayla)),
            path("iptal/<int:pk>/", self.admin_site.admin_view(self.iptal)),
            path("geldi/<int:pk>/", self.admin_site.admin_view(self.geldi)),
            path("gelmedi/<int:pk>/", self.admin_site.admin_view(self.gelmedi)),
        ]
        return custom_urls + urls

    def onayla(self, request, pk):
        """Randevuyu onayla"""
        try:
            r = get_object_or_404(Randevu, pk=pk)
            r.onayla(request.user)
            r.save()
            messages.success(request, f"✅ Randevu ONAYLANDI: {r.kullanici.username}")
            logger.info(f"Randevu Onay: {r.id} - {request.user.username}")
        except Exception as e:
            messages.error(request, f"❌ Hata: {str(e)}")
        return safe_redirect(request)

    def iptal(self, request, pk):
        """Randevuyu reddet/iptal et"""
        try:
            r = get_object_or_404(Randevu, pk=pk)
            r.sonradan_iptal()
            r.save()
            messages.warning(request, f"🔴 Randevu ReddedilDİ: {r.kullanici.username}")
            logger.info(f"Randevu Red: {r.id} - {request.user.username}")
        except Exception as e:
            messages.error(request, f"❌ Hata: {str(e)}")
        return safe_redirect(request)

    def geldi(self, request, pk):
        """Öğrenci geldi olarak işaretle"""
        try:
            r = get_object_or_404(Randevu, pk=pk)
            r.geldi_isaretle()
            r.save()
            messages.success(request, f"✅ {r.kullanici.username} GELDİ olarak işaretlendi.")
            logger.info(f"Randevu Gelişi: {r.id} - {request.user.username}")
        except Exception as e:
            messages.error(request, f"❌ Hata: {str(e)}")
        return safe_redirect(request)

    def gelmedi(self, request, pk):
        """Öğrenci gelmedi olarak işaretle"""
        try:
            r = get_object_or_404(Randevu, pk=pk)
            r.gelmedi_isaretle()
            r.save()
            messages.warning(request, f"🔴 {r.kullanici.username} GELMEDİ olarak işaretlendi.")
            logger.info(f"Randevu Gelmemesi: {r.id} - {request.user.username}")
        except Exception as e:
            messages.error(request, f"❌ Hata: {str(e)}")
        return safe_redirect(request)

# ============================================================
# ARIZA YÖNETIMI (GELİŞTİRİLMİŞ & MOBIL UYUMLU)
# ============================================================

@admin.register(Ariza)
class ArizaAdmin(admin.ModelAdmin):
    list_display = ("cihaz", "kullanici", "tarih", "aciklama_short", "cozuldu_badge", "buton")
    list_filter = ("cozuldu_mu", "tarih", "cihaz__lab")
    search_fields = ("cihaz__isim", "kullanici__username")
    date_hierarchy = "tarih"
    readonly_fields = ("tarih",)

    def aciklama_short(self, obj):
        """Arıza açıklamasını kısaltarak göster"""
        text = obj.aciklama[:50] + "..." if len(obj.aciklama) > 50 else obj.aciklama
        return format_html(
            '<span title="{}" style="cursor:help; color:#333; font-size:11px;">{}</span>',
            obj.aciklama, text
        )
    aciklama_short.short_description = "Açıklama"

    def cozuldu_badge(self, obj):
        """Arızanın çözülme durumunu badge olarak göster"""
        if obj.cozuldu_mu:
            return mark_safe('<span style="background:#28a745; color:white; padding:4px 10px; border-radius:12px; font-weight:600; font-size:11px;">✅ ÇÖZÜLDÜ</span>')
        return mark_safe('<span style="background:#dc3545; color:white; padding:4px 10px; border-radius:12px; font-weight:600; font-size:11px;">⚠️ ÇÖZÜLMEDI</span>')
    cozuldu_badge.short_description = "Durum"

    def buton(self, obj):
        """Arızayı çöz/geri al butonu - MOBIL UYUMLU"""
        if obj.cozuldu_mu:
            return format_html(
                '<a class="button" href="geri/{}/" style="{}background:#6c757d;">'
                'GERİ AL'
                '</a>',
                obj.id, BUTTON_STYLE_PRIMARY
            )
        return format_html(
            '<a class="button" href="coz/{}/" style="{}background:#28a745;">'
            '✅ ÇÖZ'
            '</a>',
            obj.id, BUTTON_STYLE_PRIMARY
        )
    buton.short_description = "İşlem"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("coz/<int:pk>/", self.admin_site.admin_view(self.coz)),
            path("geri/<int:pk>/", self.admin_site.admin_view(self.geri)),
        ]
        return custom_urls + urls

    def coz(self, request, pk):
        """Arızayı çöz"""
        try:
            a = get_object_or_404(Ariza, pk=pk)
            a.cozuldu_mu = True
            a.save()
            messages.success(request, f"✅ {a.cihaz.isim} ÇÖZÜLDÜ!")
            logger.info(f"Arıza Çözüldü: {a.cihaz.isim} - {request.user.username}")
        except Exception as e:
            messages.error(request, f"❌ Hata: {str(e)}")
        return safe_redirect(request)

    def geri(self, request, pk):
        """Arızayı geri aç"""
        try:
            a = get_object_or_404(Ariza, pk=pk)
            a.cozuldu_mu = False
            a.save()
            messages.warning(request, f"🔴 {a.cihaz.isim} arızası YENİDEN AÇILDI.")
            logger.info(f"Arıza Yeniden Açıldı: {a.cihaz.isim} - {request.user.username}")
        except Exception as e:
            messages.error(request, f"❌ Hata: {str(e)}")
        return safe_redirect(request)

# ============================================================
# KULLANICI YÖNETIMI (User & Proxy Modeller)
# ============================================================

admin.site.unregister(User)

@admin.register(User)
class CustomUserAdmin(AdminMassMailMixin, UserAdmin):
    actions = [aktif_yap, pasif_yap, mail_gonder, ozel_mail_action, super_kullanici_yap, yetkiyi_al]
    list_display = ("username", "email", "get_full_name", "is_active_badge", "is_staff_badge")
    list_filter = ("is_active", "is_staff", "date_joined")
    search_fields = ("username", "email", "first_name", "last_name")

    def get_full_name(self, obj):
        """Kullanıcının tam adını göster"""
        return obj.get_full_name() or "-"
    get_full_name.short_description = "Ad - Soyad"

    def is_active_badge(self, obj):
        """Aktiflik durumunu badge olarak göster"""
        if obj.is_active:
            return mark_safe('<span style="background:#28a745; color:white; padding:4px 10px; border-radius:12px; font-weight:600; font-size:11px;">✅ AKTİF</span>')
        return mark_safe('<span style="background:#dc3545; color:white; padding:4px 10px; border-radius:12px; font-weight:600; font-size:11px;">🔴 PASİF</span>')
    is_active_badge.short_description = "Aktivite"

    def is_staff_badge(self, obj):
        """Personel/Admin durumunu göster"""
        if obj.is_staff:
            return mark_safe('<span style="background:#0056b3; color:white; padding:4px 10px; border-radius:12px; font-weight:600; font-size:11px;">👤 PERSONEL</span>')
        return mark_safe('<span style="color:#bbb; font-size:11px;">-</span>')
    is_staff_badge.short_description = "Yetki"

@admin.register(OnayBekleyenler)
class OnayBekleyenlerAdmin(AdminMassMailMixin, UserAdmin):
    actions = [aktif_yap, mail_gonder, ozel_mail_action]
    list_display = ("username", "email", "get_full_name", "aktiflik_durumu", "tek_tik_aktif_et")
    list_filter = ("date_joined",)
    search_fields = ("username", "email")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_active=False)

    def get_full_name(self, obj):
        return obj.get_full_name() or "-"
    get_full_name.short_description = "Ad - Soyad"

    def aktiflik_durumu(self, obj):
        return mark_safe('<span style="background:#dc3545; color:white; padding:4px 10px; border-radius:12px; font-weight:600; font-size:11px;">🔴 PASİF</span>')
    aktiflik_durumu.short_description = "Durum"

    def tek_tik_aktif_et(self, obj):
        return format_html(
            '<a class="button" href="aktif-et/{}/" style="{}background:#28a745;">'
            'AKTİF ET'
            '</a>',
            obj.id, BUTTON_STYLE_PRIMARY
        )
    tek_tik_aktif_et.short_description = "Hızlı İşlem"

    def get_urls(self):
        urls = super().get_urls()
        return [path("aktif-et/<int:pk>/", self.admin_site.admin_view(self.aktif_et))] + urls

    def aktif_et(self, request, pk):
        """Kullanıcıyı aktif et"""
        try:
            u = get_object_or_404(User, pk=pk)
            u.is_active = True
            u.save()
            messages.success(request, f"✅ {u.username} AKTİF edildi!")
            logger.info(f"Kullanıcı Aktifleştirildi: {u.username}")
        except Exception as e:
            messages.error(request, f"❌ Hata: {str(e)}")
        return safe_redirect(request)

@admin.register(AktifKullanicilar)
class AktifKullanicilarAdmin(AdminMassMailMixin, UserAdmin):
    actions = [pasif_yap, mail_gonder, ozel_mail_action]
    list_display = ("username", "email", "get_full_name", "aktiflik_durumu", "tek_tik_pasif_et")
    list_filter = ("date_joined",)
    search_fields = ("username", "email")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_active=True)

    def get_full_name(self, obj):
        return obj.get_full_name() or "-"
    get_full_name.short_description = "Ad - Soyad"

    def aktiflik_durumu(self, obj):
        return mark_safe('<span style="background:#28a745; color:white; padding:4px 10px; border-radius:12px; font-weight:600; font-size:11px;">✅ AKTİF</span>')
    aktiflik_durumu.short_description = "Durum"

    def tek_tik_pasif_et(self, obj):
        return format_html(
            '<a class="button" href="pasif-et/{}/" style="{}background:#dc3545;">'
            'PASİF ET'
            '</a>',
            obj.id, BUTTON_STYLE_PRIMARY
        )
    tek_tik_pasif_et.short_description = "Hızlı İşlem"

    def get_urls(self):
        urls = super().get_urls()
        return [path("pasif-et/<int:pk>/", self.admin_site.admin_view(self.pasif_et))] + urls

    def pasif_et(self, request, pk):
        """Kullanıcıyı pasif et"""
        try:
            u = get_object_or_404(User, pk=pk)
            u.is_active = False
            u.save()
            messages.warning(request, f"🔴 {u.username} PASİF yapıldı.")
            logger.info(f"Kullanıcı Pasifleştirildi: {u.username}")
        except Exception as e:
            messages.error(request, f"❌ Hata: {str(e)}")
        return safe_redirect(request)

# ============================================================
# PROFİL YÖNETIMI - EMAIL DOĞRULAMA VE STATUS
# ============================================================

@admin.register(Profil)
class ProfilAdmin(AdminMassMailMixin, admin.ModelAdmin):
    """
    Profil Yönetimi: Email doğrulama ve öğrenci statüsü kontrolü
    """
    list_display = ("user", "okul_numarasi", "telefon", "status_badge", "email_dogrulandi_display", "email_dogrulama_tarihi", "resim_preview")
    list_filter = ("status", "email_dogrulandi", "email_dogrulama_tarihi")
    search_fields = ("user__username", "user__email", "okul_numarasi", "telefon")
    readonly_fields = ("email_dogrulama_tarihi", "email_dogrulandi_display", "status_display")
    actions = ["studentleri_aktif_et", "studentleri_pasif_et", "studentleri_iptal_et", "ozel_mail_action"]
    
    fieldsets = (
        ("Kullanıcı Bilgileri", {
            'fields': ('user', 'okul_numarasi', 'telefon')
        }),
        ("Email Doğrulama", {
            'fields': ('email_dogrulandi_display', 'email_dogrulama_tarihi'),
            'description': '✅ Email doğrulama statüsü (Bu alanlar otomatik olarak güncellenir)'
        }),
        ("Öğrenci Statüsü", {
            'fields': ('status_display', 'status'),
            'description': '⚠️ Status değiştirilirse User.is_active otomatik güncellenir'
        }),
        ("Profil Resmi", {
            'fields': ('resim',),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        """Status'u renk-kodlu badge olarak göster"""
        colors = {
            'pasif_kullanici': '#ffc107',      # Sarı
            'aktif_kullanici': '#28a745',      # Yeşil
            'iptal': '#dc3545',               # Kırmızı
        }
        labels = {
            'pasif_kullanici': '⏳ Pasif Kullanıcı',
            'aktif_kullanici': '✅ Aktif Kullanıcı',
            'iptal': '❌ İptal',
        }
        color = colors.get(obj.status, '#6c757d')
        label = labels.get(obj.status, 'Bilinmiyor')
        text_color = '#000' if obj.status == 'pasif_kullanici' else '#fff'
        
        return mark_safe(
            f'<span style="background:{color}; color:{text_color}; padding:6px 12px; '
            f'border-radius:14px; font-weight:600; font-size:11px; display:inline-block;">'
            f'{label}</span>'
        )
    status_badge.short_description = "Statü"

    def status_display(self, obj):
        """Status seçim alanı için açıklama göster"""
        return f"Mevcut: {obj.get_status_display()}"
    status_display.short_description = "Mevcut Statü"

    def email_dogrulandi_display(self, obj):
        """Email doğrulama durumunu göster"""
        if obj.email_dogrulandi:
            return mark_safe(
                '<span style="background:#28a745; color:white; padding:4px 10px; '
                'border-radius:12px; font-weight:600; font-size:11px;">✅ DOĞRULANDI</span>'
            )
        return mark_safe(
            '<span style="background:#dc3545; color:white; padding:4px 10px; '
            'border-radius:12px; font-weight:600; font-size:11px;">⏳ BEKLEMEDE</span>'
        )
    email_dogrulandi_display.short_description = "Email Durumu"

    def resim_preview(self, obj):
        """Profil resimini küçük ön izlemede göster"""
        if obj.resim:
            return format_html(
                '<img src="{}" width="30" height="30" style="border-radius:50%; border:2px solid #0056b3;" />',
                obj.resim.url
            )
        return mark_safe('<span style="color:#bbb;">Yok</span>')
    resim_preview.short_description = "Resim"

    # ============================================================
    # STATÜ DEĞİŞTİRME AKSIYON FONKSİYONLARI
    # ============================================================

    @admin.action(description="✅ Seçilenleri AKTİF Öğrenci Yap")
    def studentleri_aktif_et(self, request, queryset):
        """Seçili öğrencileri aktif et"""
        try:
            updated = 0
            for profil in queryset:
                profil.status = 'aktif_kullanici'
                profil.user.is_active = True
                profil.save()
                profil.user.save()
                updated += 1
            
            messages.success(
                request, 
                f"✅ {updated} öğrenci AKTİF edildi! Login yapabilecekler."
            )
            logger.info(f"Öğrenciler Aktifleştirildi: {updated} - {request.user.username}")
        except Exception as e:
            messages.error(request, f"❌ Hata: {str(e)}")

    @admin.action(description="⏳ Seçilenleri PASİF Öğrenci Yap")
    def studentleri_pasif_et(self, request, queryset):
        """Seçili öğrencileri pasif et"""
        try:
            updated = 0
            for profil in queryset:
                profil.status = 'pasif_kullanici'
                profil.user.is_active = False
                profil.save()
                profil.user.save()
                updated += 1
            
            messages.warning(
                request, 
                f"⏳ {updated} öğrenci PASİF yapıldı. Login yapamayacaklar."
            )
            logger.info(f"Öğrenciler Pasifleştirildi: {updated} - {request.user.username}")
        except Exception as e:
            messages.error(request, f"❌ Hata: {str(e)}")

    @admin.action(description="❌ Seçilenleri İPTAL Et")
    def studentleri_iptal_et(self, request, queryset):
        """Seçili öğrencileri iptal et"""
        try:
            updated = 0
            for profil in queryset:
                profil.status = 'iptal'
                profil.user.is_active = False
                profil.save()
                profil.user.save()
                updated += 1
            
            messages.error(
                request, 
                f"❌ {updated} öğrenci İPTAL edildi."
            )
            logger.info(f"Öğrenciler İptal Edildi: {updated} - {request.user.username}")
        except Exception as e:
            messages.error(request, f"❌ Hata: {str(e)}")

# ============================================================
# DUYURU YÖNETIMI (GELİŞTİRİLMİŞ & MOBIL UYUMLU)
# ============================================================

@admin.register(Duyuru)
class DuyuruAdmin(admin.ModelAdmin):
    list_display = ("baslik", "tarih", "aktif_mi_badge", "hizli_islem")
    list_filter = ("aktif_mi", "tarih")
    search_fields = ("baslik", "icerik")
    date_hierarchy = "tarih"
    readonly_fields = ("tarih",)
    actions = ["duyuru_aktif_et", "duyuru_pasif_et"]
    
    fieldsets = (
        ("Duyuru İçeriği", {
            'fields': ('baslik', 'icerik', 'aktif_mi')
        }),
        ("Bilgiler", {
            'fields': ('tarih',),
            'classes': ('collapse',)
        }),
    )

    def aktif_mi_badge(self, obj):
        """Duyurunun aktif olup olmadığını göster"""
        if obj.aktif_mi:
            return mark_safe('<span style="background:#28a745; color:white; padding:4px 10px; border-radius:12px; font-weight:600; font-size:11px;">📢 AKTİF</span>')
        return mark_safe('<span style="background:#6c757d; color:white; padding:4px 10px; border-radius:12px; font-weight:600; font-size:11px;">⊘ PASİF</span>')
    aktif_mi_badge.short_description = "Durum"

    def hizli_islem(self, obj):
        """Duyuru durumunu hızlı değiştir - MOBIL UYUMLU"""
        if not obj.aktif_mi:
            return format_html(
                '<a class="button" href="aktif-et/{}/" style="{}background:#28a745;">'
                '📢 YAYINLA'
                '</a>',
                obj.id, BUTTON_STYLE_PRIMARY
            )
        else:
            return format_html(
                '<a class="button" href="pasif-et/{}/" style="{}background:#dc3545;">'
                '🔴 KALDIR'
                '</a>',
                obj.id, BUTTON_STYLE_PRIMARY
            )
    hizli_islem.short_description = "İşlem"

    @admin.action(description="📢 Seçilenleri Yayınla")
    def duyuru_aktif_et(self, request, queryset):
        """Seçili duyuruları yayınla"""
        updated = queryset.update(aktif_mi=True)
        messages.success(request, f"✅ {updated} duyuru YAYINLANDI!")
        logger.info(f"Duyuru Yayınlandı: {updated} - {request.user.username}")

    @admin.action(description="🔴 Seçilenleri Kaldır")
    def duyuru_pasif_et(self, request, queryset):
        """Seçili duyuruları kaldır"""
        updated = queryset.update(aktif_mi=False)
        messages.warning(request, f"🔴 {updated} duyuru KALDIRILDI.")
        logger.info(f"Duyuru Kaldırıldı: {updated} - {request.user.username}")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("aktif-et/<int:pk>/", self.admin_site.admin_view(self.aktif_et_single)),
            path("pasif-et/<int:pk>/", self.admin_site.admin_view(self.pasif_et_single)),
        ]
        return custom_urls + urls

    def aktif_et_single(self, request, pk):
        """Tek duyuruyu yayınla"""
        try:
            d = get_object_or_404(Duyuru, pk=pk)
            d.aktif_mi = True
            d.save()
            messages.success(request, f"✅ '{d.baslik}' YAYINLANDI!")
            logger.info(f"Duyuru Yayıncılıklandı: {d.baslik}")
        except Exception as e:
            messages.error(request, f"❌ Hata: {str(e)}")
        return safe_redirect(request)

    def pasif_et_single(self, request, pk):
        """Tek duyuruyu kaldır"""
        try:
            d = get_object_or_404(Duyuru, pk=pk)
            d.aktif_mi = False
            d.save()
            messages.warning(request, f"🔴 '{d.baslik}' KALDIRILDI.")
            logger.info(f"Duyuru Kaldırıldı: {d.baslik}")
        except Exception as e:
            messages.error(request, f"❌ Hata: {str(e)}")
        return safe_redirect(request)