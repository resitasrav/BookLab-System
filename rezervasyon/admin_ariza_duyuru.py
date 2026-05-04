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

# TURKCE ARAMA: ariza admin, duyuru admin, teknik bakim
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
