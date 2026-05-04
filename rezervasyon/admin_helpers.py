# TURKCE ARAMA: admin yardimcilari, admin aksiyonlari, mail gonderme, guvenli redirect

import csv
import logging

from django.apps import apps
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives, send_mail
from django.core.validators import validate_email
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import path
from django.utils.html import strip_tags
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import AdminMassEmailForm

logger = logging.getLogger('admin_operations')

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
                # HTML şablonu render et
                html_content = render_to_string(
                    "emails/bilgilendirme.html",
                    {
                        "ad": user.get_full_name() or user.username,
                        "mesaj": "Hesabınızla ilgili önemli bir bildirimi size göndermekteyiz.",
                    }
                )
                
                # Düz metin versiyonu oluştur
                text_content = strip_tags(html_content)
                
                # Email nesnesini oluştur
                email_obj = EmailMultiAlternatives(
                    subject="BookLab Sistemi - Bilgilendirme",
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[user.email],
                )
                
                # HTML versiyonunu ekle
                email_obj.attach_alternative(html_content, "text/html")
                email_obj.send()
                
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
    """Seçili kullanıcıları aktif hale getir ve profillerini senkronize et"""
    updated = 0
    for obj in queryset:
        user = obj if isinstance(obj, User) else getattr(obj, 'user', getattr(obj, 'kullanici', None))
        if user:
            user.is_active = True
            user.save()
            if hasattr(user, 'profil'):
                user.profil.status = 'aktif_kullanici'
                user.profil.save()
            updated += 1
            
    modeladmin.message_user(request, f"✅ {updated} kullanıcı aktif yapıldı.", messages.SUCCESS)
    logger.info(f"Aktifleştirme: {request.user.username} - {updated} kayıt")

@admin.action(description="🔴 Pasif Yap")
def pasif_yap(modeladmin, request, queryset):
    """Seçili kullanıcıları pasif hale getir ve profillerini senkronize et"""
    updated = 0
    for obj in queryset:
        user = obj if isinstance(obj, User) else getattr(obj, 'user', getattr(obj, 'kullanici', None))
        if user:
            user.is_active = False
            user.save()
            if hasattr(user, 'profil'):
                user.profil.status = 'pasif_kullanici'
                user.profil.save()
            updated += 1
            
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

                    # Yeni HTML şablonu kullanılarak içeriği oluşturuyoruz
                    html_content = render_to_string(
                        "emails/admin_ozel_mail.html",
                        {
                            "subject": subject,
                            "message": message,
                            "is_html": is_html
                        }
                    )
                    text_content = strip_tags(html_content)

                    sent = 0
                    failed = 0
                    errors = []

                    for _obj, email in recipients:
                        try:
                            msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [email])
                            msg.attach_alternative(html_content, "text/html")
                            msg.send(fail_silently=False)
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
