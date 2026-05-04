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

# TURKCE ARAMA: randevu admin, randevu onay, geldi gelmedi, csv
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
