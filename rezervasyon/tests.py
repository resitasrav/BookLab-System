from datetime import date, time

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Cihaz, Laboratuvar, Randevu


class RandevuKurallariTestleri(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ogrenci", password="testpass123")
        self.lab = Laboratuvar.objects.create(isim="Kimya Lab")
        self.cihaz = Cihaz.objects.create(lab=self.lab, isim="Mikroskop")

    def test_ayni_cihazda_cakisan_randevu_engellenir(self):
        Randevu.objects.create(
            kullanici=self.user,
            cihaz=self.cihaz,
            tarih=date(2026, 6, 1),
            baslangic_saati=time(10, 0),
            bitis_saati=time(11, 0),
        )

        ikinci = Randevu(
            kullanici=self.user,
            cihaz=self.cihaz,
            tarih=date(2026, 6, 1),
            baslangic_saati=time(10, 30),
            bitis_saati=time(11, 30),
        )

        with self.assertRaises(ValidationError):
            ikinci.full_clean()

    def test_iptal_edilen_randevu_cakisma_olusturmaz(self):
        Randevu.objects.create(
            kullanici=self.user,
            cihaz=self.cihaz,
            tarih=date(2026, 6, 1),
            baslangic_saati=time(10, 0),
            bitis_saati=time(11, 0),
            durum=Randevu.IPTAL,
        )

        yeni = Randevu(
            kullanici=self.user,
            cihaz=self.cihaz,
            tarih=date(2026, 6, 1),
            baslangic_saati=time(10, 0),
            bitis_saati=time(11, 0),
        )
        yeni.full_clean()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class GuvenliIslemTestleri(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            password="testpass123",
            is_staff=True,
            is_superuser=True,
        )
        self.user = User.objects.create_user(username="ogrenci", password="testpass123")
        self.lab = Laboratuvar.objects.create(isim="Fizik Lab")
        self.cihaz = Cihaz.objects.create(lab=self.lab, isim="Osiloskop")
        self.randevu = Randevu.objects.create(
            kullanici=self.user,
            cihaz=self.cihaz,
            tarih=date(2026, 6, 1),
            baslangic_saati=time(10, 0),
            bitis_saati=time(11, 0),
        )

    def test_durum_guncelleme_get_ile_calismamalidir(self):
        self.client.force_login(self.admin)
        url = reverse("durum_guncelle", args=[self.randevu.id, Randevu.ONAYLANDI])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)

    def test_durum_guncelleme_gecersiz_durumu_kaydetmez(self):
        self.client.force_login(self.admin)
        url = reverse("durum_guncelle", args=[self.randevu.id, "gecersiz"])

        self.client.post(url)
        self.randevu.refresh_from_db()

        self.assertEqual(self.randevu.durum, Randevu.ONAY_BEKLENIYOR)

    def test_randevu_iptali_get_ile_calismamalidir(self):
        self.client.force_login(self.user)
        url = reverse("randevu_iptal", args=[self.randevu.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)
