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

# TURKCE ARAMA: laboratuvar admin, cihaz admin, cihaz durum islemleri
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
