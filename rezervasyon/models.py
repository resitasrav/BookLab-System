from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver

# 1. Kapsayıcı: Laboratuvar
class Laboratuvar(models.Model):
    isim = models.CharField(max_length=100, verbose_name="Laboratuvar Adı")
    aciklama = models.TextField(blank=True, verbose_name="Açıklama")

    class Meta:
        verbose_name = "Laboratuvar"
        verbose_name_plural = "Laboratuvarlar"

    def __str__(self):
        return self.isim


# 2. Rezerve Edilecek Nesne: Cihaz
# 2. Rezerve Edilecek Nesne: Cihaz
class Cihaz(models.Model):
    lab = models.ForeignKey(Laboratuvar, on_delete=models.CASCADE, verbose_name="Bağlı Olduğu Laboratuvar")
    isim = models.CharField(max_length=100, verbose_name="Cihaz Adı")
    aktif_mi = models.BooleanField(default=True, verbose_name="Kullanıma Açık mı?")
    aciklama = models.TextField(blank=True, null=True, verbose_name="Açıklama")
    resim = models.ImageField(upload_to="cihazlar/", blank=True, null=True, verbose_name="Cihaz Resmi")

    class Meta:
        verbose_name = "Cihaz"
        verbose_name_plural = "Cihazlar"

    def __str__(self):
        return f"{self.isim} ({self.lab.isim})"


    @property
    def son_ariza_notu(self):
        # Bu cihaza ait olan ve henüz çözülmemiş en son arıza kaydını bul
        son_ariza = self.ariza_set.filter(cozuldu_mu=False).last() 
        if son_ariza:
            return son_ariza.aciklama
        return "Manuel pasife alındı veya not yok."

# 3. İşlem: Randevu
class Randevu(models.Model):
    # DURUM SABİTLERİ 
    ONAY_BEKLENIYOR = "onay_bekleniyor"
    ONAYLANDI = "onaylandi"
    REDDEDILDI = "reddedildi"
    GELDI = "geldi"
    GELMEDI = "gelmedi"
    IPTAL = "iptal_edildi"

    DURUM_SECENEKLERI = [
        (ONAY_BEKLENIYOR, "Onay Bekleniyor"),
        (ONAYLANDI, "Onaylandı"),
        (REDDEDILDI, "Reddedildi"),
        (GELDI, "Geldi"),
        (GELMEDI, "Gelmedi"),
        (IPTAL, "İptal Edildi"),
    ]

    kullanici = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Randevuyu Alan")
    cihaz = models.ForeignKey(Cihaz, on_delete=models.PROTECT, verbose_name="Seçilen Cihaz")
    tarih = models.DateField(verbose_name="Randevu Tarihi")
    baslangic_saati = models.TimeField(verbose_name="Başlangıç Saati")
    bitis_saati = models.TimeField(verbose_name="Bitiş Saati")
    olusturulma_zamani = models.DateTimeField(auto_now_add=True)

    durum = models.CharField(
        max_length=20,
        choices=DURUM_SECENEKLERI,
        default=ONAY_BEKLENIYOR, 
        verbose_name="Rezervasyon Durumu",
    )

    onaylayan_admin = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="İşlemi Yapan Yönetici",
        related_name="onaylanan_randevular",
    )

    class Meta:
        verbose_name = "Randevu"
        verbose_name_plural = "Randevular"

    def __str__(self):
        return f"{self.kullanici.username} - {self.cihaz.isim} - {self.tarih}"

    def clean(self):
        if self.durum != self.IPTAL:
            # Çakışma kontrolü
            cakisma_var_mi = Randevu.objects.filter(
                cihaz=self.cihaz, 
                tarih=self.tarih, 
                durum__in=[self.ONAY_BEKLENIYOR, self.ONAYLANDI, self.GELDI]
            ).exclude(pk=self.pk)

            cakisma = cakisma_var_mi.filter(
                baslangic_saati__lt=self.bitis_saati,
                bitis_saati__gt=self.baslangic_saati,
            )

            if cakisma.exists():
                raise ValidationError("Bu saat aralığında bu cihaz için başka bir randevu zaten mevcut!")

            if self.baslangic_saati >= self.bitis_saati:
                raise ValidationError("Başlangıç saati, bitiş saatinden sonra veya aynı olamaz.")
    def onayla(self, admin_user):
        """Randevuyu onaylar ve admini kaydeder"""
        self.durum = self.ONAYLANDI
        self.onaylayan_admin = admin_user

    def geldi_isaretle(self):
        """Kullanıcının laboratuvara geldiğini kaydeder"""
        self.durum = self.GELDI

    def gelmedi_isaretle(self):
        """Kullanıcının randevuya gelmediğini kaydeder"""
        self.durum = self.GELMEDI

    def sonradan_iptal(self):
        """Herhangi bir aşamada randevuyu iptal/red durumuna çeker"""
        self.durum = self.REDDEDILDI  # Veya self.IPTAL
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

# 4. Profil
class Profil(models.Model):
    # ✨ ÖĞRENCI STATUS SEÇENEKLERI
    STATUS_CHOICES = [
        ('pasif_kullanici', 'Pasif kullanıcı (Email Doğrulı)'),
        ('aktif_kullanici', 'Aktif Kullanıcı (Admin Onaylı)'),
        ('iptal', 'İptal Edildi'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Kullanıcı")
    okul_numarasi = models.CharField(max_length=20, blank=True, verbose_name="Okul Numarası")
    telefon = models.CharField(max_length=15, blank=True, verbose_name="Telefon Numarası")
    resim = models.ImageField(upload_to="profil_resimleri/", blank=True, null=True, verbose_name="Profil Resmi")
    dogrulama_kodu = models.CharField(max_length=6, blank=True, null=True, verbose_name="E-Posta Doğrulama Kodu")
    kod_olusturma_tarihi = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pasif_kullanici',
        verbose_name="Kullanıcı Durumu"
    )
    email_dogrulandi = models.BooleanField(
        default=False,
        verbose_name="Email Doğrulandı mı?"
    )
    email_dogrulama_tarihi = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Email Doğrulama Tarihi"
    )

    class Meta:
        verbose_name = "Kullanıcı Profili"
        verbose_name_plural = "Kullanıcı Profilleri"

    def __str__(self):
        return f"{self.user.username} Profili"

@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    profil, created = Profil.objects.get_or_create(user=instance)
    profil.save()


# 5. Arıza Bildirimi
class Ariza(models.Model):
    kullanici = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Bildiren Kişi")
    cihaz = models.ForeignKey(Cihaz, on_delete=models.CASCADE, verbose_name="Arızalı Cihaz")
    aciklama = models.TextField(verbose_name="Arıza Açıklaması")
    cozuldu_mu = models.BooleanField(default=False, verbose_name="Çözüldü mü?")
    tarih = models.DateTimeField(auto_now_add=True, verbose_name="Bildirim Tarihi")

    class Meta:
        verbose_name = "Arıza Bildirimi"
        verbose_name_plural = "Arıza Bildirimleri"
        ordering = ["-tarih"]
    
    def __str__(self):
        return f"Arıza: {self.cihaz.isim} - {self.kullanici.username}"
        

# 6. Duyurular
class Duyuru(models.Model):
    baslik = models.CharField(max_length=200, verbose_name="Duyuru Başlığı")
    icerik = models.TextField(blank=True, verbose_name="Duyuru İçeriği")
    aktif_mi = models.BooleanField(default=True, verbose_name="Yayında mı?")
    tarih = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Duyuru"
        verbose_name_plural = "Duyurular"
        ordering = ["-tarih"]
    
    def __str__(self):
        return self.baslik


# 7. Proxy Modeller
class OnayBekleyenler(User):
    class Meta:
        proxy = True
        verbose_name = "Onay Bekleyen (Pasif)"
        verbose_name_plural = "🔴 Onay Bekleyenler"

class AktifKullanicilar(User):
    class Meta:
        proxy = True
        verbose_name = "Aktif Kullanıcı"
        verbose_name_plural = "🟢 Aktif Kullanıcılar"
