# TURKCE ARAMA: model admin kayitlari, Django admin bolunmus moduller

import logging

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.db import models
from django.shortcuts import get_object_or_404, redirect
from django.urls import path
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .admin_helpers import (
    BUTTON_STYLE_PRIMARY,
    BUTTON_STYLE_SUCCESS,
    BUTTON_STYLE_DANGER,
    BUTTON_STYLE_INFO,
    BUTTON_STYLE_WARNING,
    BUTTON_STYLE_SECONDARY,
    BUTTON_WRAPPER,
    AdminMassMailMixin,
    aktif_yap,
    excel_indir,
    mail_gonder,
    ozel_mail_action,
    pasif_yap,
    safe_redirect,
    super_kullanici_yap,
    yetkiyi_al,
)
from .models import (
    Laboratuvar,
    Cihaz,
    Randevu,
    Profil,
    Ariza,
    Duyuru,
    OnayBekleyenler,
    AktifKullanicilar,
)

logger = logging.getLogger('admin_operations')

# TURKCE ARAMA: kullanici admin, profil admin, onay bekleyen, aktif kullanici
@admin.register(User)
class CustomUserAdmin(AdminMassMailMixin, UserAdmin):
    actions = [aktif_yap, pasif_yap, mail_gonder, ozel_mail_action, super_kullanici_yap, yetkiyi_al]
    list_display = ("username", "email", "get_full_name", "is_active_badge", "is_staff_badge")
    list_filter = ("is_active", "is_staff", "date_joined")
    search_fields = ("username", "email", "first_name", "last_name")

    def save_model(self, request, obj, form, change):
        """Form üzerinden yapılan düzenlemelerde superuser koruması.
        Kural 1: Superuser kendi hesabını pasif yapamaz.
        Kural 2: Superuser kendi yetkisini düşüremez.
        Kural 3: Son aktif superuser'ın yetkisi/aktifliği kaldırılamaz.
        """
        if change:
            try:
                original = User.objects.get(pk=obj.pk)
            except User.DoesNotExist:
                original = None

            if original:
                # Kural 1: Kendi hesabını pasif yapamaz
                if obj.pk == request.user.pk and not obj.is_active:
                    self.message_user(request, "❌ Kendinizi pasif yapamazsınız! Değişiklik geri alındı.", messages.ERROR)
                    obj.is_active = True

                # Kural 2: Kendi superuser yetkisini düşüremez
                if obj.pk == request.user.pk and original.is_superuser and not obj.is_superuser:
                    self.message_user(request, "❌ Kendi yönetici yetkinizi düşüremezsiniz! Değişiklik geri alındı.", messages.ERROR)
                    obj.is_superuser = True
                    obj.is_staff = True

                # Kural 3: Son aktif superuser' ın yetkisi/aktifliği kaldırılamaz
                if original.is_superuser and (not obj.is_superuser or not obj.is_active):
                    aktif_superuser_sayisi = User.objects.filter(
                        is_superuser=True, is_active=True
                    ).exclude(pk=obj.pk).count()
                    if aktif_superuser_sayisi == 0:
                        self.message_user(
                            request,
                            f"❌ {obj.username} son aktif yöneticidir; yetkisi veya aktifliği kaldırılamaz! Değişiklik geri alındı.",
                            messages.ERROR
                        )
                        obj.is_superuser = original.is_superuser
                        obj.is_staff = original.is_staff
                        obj.is_active = original.is_active

        super().save_model(request, obj, form, change)

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
            if hasattr(u, 'profil'):
                u.profil.status = 'aktif_kullanici'
                u.profil.save()
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
        """Kullanıcıyı pasif et.
        Kural 1: Superuser kendisini pasif yapamaz.
        Kural 2: Superuser pasif yapılamaz (son aktif superuser kesinlikle yapılamaz).
        """
        try:
            u = get_object_or_404(User, pk=pk)

            # Kural 1: Kendini pasif yapamaz
            if u == request.user:
                messages.error(request, "❌ Kendinizi pasif yapamazsınız!")
                return safe_redirect(request)

            # Kural 2: Superuser pasif yapılamaz
            if u.is_superuser:
                aktif_superuser_sayisi = User.objects.filter(is_superuser=True, is_active=True).count()
                if aktif_superuser_sayisi <= 1:
                    messages.error(request, f"❌ {u.username} son aktif yöneticidir, pasif yapılamaz!")
                else:
                    messages.error(request, f"❌ {u.username} bir yöneticidir (superuser), pasif yapılamaz!")
                return safe_redirect(request)

            u.is_active = False
            u.save()
            if hasattr(u, 'profil'):
                u.profil.status = 'pasif_kullanici'
                u.profil.save()
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
    list_display = ("user", "telefon", "status_badge", "email_dogrulandi_display", "email_dogrulama_tarihi", "resim_preview")
    list_filter = ("status", "email_dogrulandi", "email_dogrulama_tarihi")
    search_fields = ("user__username", "user__email", "telefon")
    readonly_fields = ("email_dogrulama_tarihi", "email_dogrulandi_display", "status_display")
    actions = ["studentleri_aktif_et", "studentleri_pasif_et", "studentleri_iptal_et", "ozel_mail_action"]
    
    fieldsets = (
        ("Kullanıcı Bilgileri", {
            'fields': ('user', 'telefon')
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
        """Seçili öğrencileri pasif et (superuser profilleri korunur)"""
        try:
            updated = 0
            atlanan = 0
            for profil in queryset:
                # Superuser profilleri pasif yapılamaz
                if profil.user.is_superuser:
                    atlanan += 1
                    continue
                # Kendi profilini pasif yapamaz
                if profil.user == request.user:
                    atlanan += 1
                    continue
                profil.status = 'pasif_kullanici'
                profil.user.is_active = False
                profil.save()
                profil.user.save()
                updated += 1

            if updated > 0:
                messages.warning(
                    request,
                    f"⏳ {updated} öğrenci PASİF yapıldı. Login yapamayacaklar."
                )
            if atlanan > 0:
                messages.error(
                    request,
                    f"⚠️ {atlanan} kullanıcı atlandı (yönetici profilleri değiştirilemez)."
                )
            logger.info(f"Öğrenciler Pasifleştirildi: {updated} - {request.user.username}")
        except Exception as e:
            messages.error(request, f"❌ Hata: {str(e)}")

    @admin.action(description="❌ Seçilenleri İPTAL Et")
    def studentleri_iptal_et(self, request, queryset):
        """Seçili öğrencileri iptal et (superuser profilleri korunur)"""
        try:
            updated = 0
            atlanan = 0
            for profil in queryset:
                # Superuser profilleri iptal edilemez
                if profil.user.is_superuser:
                    atlanan += 1
                    continue
                # Kendi profilini iptal edemez
                if profil.user == request.user:
                    atlanan += 1
                    continue
                profil.status = 'iptal'
                profil.user.is_active = False
                profil.save()
                profil.user.save()
                updated += 1

            if updated > 0:
                messages.error(
                    request,
                    f"❌ {updated} öğrenci İPTAL edildi."
                )
            if atlanan > 0:
                messages.warning(
                    request,
                    f"⚠️ {atlanan} kullanıcı atlandı (yönetici profilleri değiştirilemez)."
                )
            logger.info(f"Öğrenciler İptal Edildi: {updated} - {request.user.username}")
        except Exception as e:
            messages.error(request, f"❌ Hata: {str(e)}")


# ============================================================
# DUYURU YÖNETIMI (GELİŞTİRİLMİŞ & MOBIL UYUMLU)
# ============================================================
