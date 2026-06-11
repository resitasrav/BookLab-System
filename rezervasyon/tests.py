from datetime import date, datetime, time, timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Cihaz, Laboratuvar, Randevu
from .view_helpers import otomatik_geldi_isaretle, saat_yuvarla


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
            durum=Randevu.ONAYLANDI,
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

        # Geçersiz durum kaydedilmemeli; randevu oluşturulduğu gibi kalmalı.
        self.assertEqual(self.randevu.durum, Randevu.ONAYLANDI)

    def test_randevu_iptali_get_ile_calismamalidir(self):
        self.client.force_login(self.user)
        url = reverse("randevu_iptal", args=[self.randevu.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)


class IsKuraliTestleri(TestCase):
    """Otomatik onay, 48 saat otomatik geldi ve saat yuvarlama kuralları."""

    def setUp(self):
        self.user = User.objects.create_user(username="ogrenci", password="testpass123")
        self.lab = Laboratuvar.objects.create(isim="Biyoloji Lab")
        self.cihaz = Cihaz.objects.create(lab=self.lab, isim="Santrifüj")

    def test_yeni_randevu_otomatik_onaylanir(self):
        r = Randevu.objects.create(
            kullanici=self.user,
            cihaz=self.cihaz,
            tarih=date(2099, 1, 1),
            baslangic_saati=time(10, 0),
            bitis_saati=time(11, 0),
        )
        self.assertEqual(r.durum, Randevu.ONAYLANDI)

    def test_48_saat_gecmis_onayli_randevu_otomatik_geldi_olur(self):
        gecmis = (timezone.now() - timedelta(hours=72)).date()
        r = Randevu.objects.create(
            kullanici=self.user,
            cihaz=self.cihaz,
            tarih=gecmis,
            baslangic_saati=time(9, 0),
            bitis_saati=time(10, 0),
            durum=Randevu.ONAYLANDI,
        )
        guncellenen = otomatik_geldi_isaretle()
        r.refresh_from_db()
        self.assertEqual(guncellenen, 1)
        self.assertEqual(r.durum, Randevu.GELDI)

    def test_gelmedi_isaretli_randevu_otomatik_gelmez(self):
        gecmis = (timezone.now() - timedelta(hours=72)).date()
        r = Randevu.objects.create(
            kullanici=self.user,
            cihaz=self.cihaz,
            tarih=gecmis,
            baslangic_saati=time(9, 0),
            bitis_saati=time(10, 0),
            durum=Randevu.GELMEDI,
        )
        otomatik_geldi_isaretle()
        r.refresh_from_db()
        self.assertEqual(r.durum, Randevu.GELMEDI)

    def test_yakin_zamanli_randevu_otomatik_geldi_olmaz(self):
        yakin = (timezone.now() - timedelta(hours=2)).date()
        r = Randevu.objects.create(
            kullanici=self.user,
            cihaz=self.cihaz,
            tarih=yakin,
            baslangic_saati=time(0, 0),
            bitis_saati=time(0, 10),
            durum=Randevu.ONAYLANDI,
        )
        otomatik_geldi_isaretle()
        r.refresh_from_db()
        self.assertEqual(r.durum, Randevu.ONAYLANDI)

    def test_saat_yuvarla_en_yakin_10a_yuvarlar(self):
        self.assertEqual(saat_yuvarla(datetime(2026, 1, 1, 9, 7)).time(), time(9, 10))
        self.assertEqual(saat_yuvarla(datetime(2026, 1, 1, 9, 4)).time(), time(9, 0))
        self.assertEqual(saat_yuvarla(datetime(2026, 1, 1, 9, 58)).time(), time(10, 0))


class TopluRandevuTestleri(TestCase):
    """Yönetici toplu randevu oluşturma akışı."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin", password="x", is_staff=True, is_superuser=True
        )
        self.hedef = User.objects.create_user(username="hedef", password="x")
        self.lab = Laboratuvar.objects.create(isim="Lab")
        self.cihaz = Cihaz.objects.create(lab=self.lab, isim="Cihaz")
        self.ileri = (timezone.now() + timedelta(days=10)).date().isoformat()

    def test_araliktan_randevu_olusur(self):
        # İlk slot başlangıç, ikinci slot bitiş: 09:00-09:30 tek randevu olur
        self.client.force_login(self.admin)
        self.client.post("/yonetim/toplu-randevu/", {
            "cihaz": self.cihaz.id,
            "tarih": self.ileri,
            "kullanici": self.hedef.id,
            "aralik": ["09:00-09:30"],
        })
        randevular = Randevu.objects.filter(cihaz=self.cihaz, tarih=self.ileri)
        self.assertEqual(randevular.count(), 1)
        r = randevular.first()
        self.assertEqual(r.baslangic_saati, time(9, 0))
        self.assertEqual(r.bitis_saati, time(9, 30))
        # Yönetici oluşturduğu için doğrudan onaylı
        self.assertEqual(r.durum, Randevu.ONAYLANDI)

    def test_coklu_aralik_ayri_randevu_olusur(self):
        self.client.force_login(self.admin)
        self.client.post("/yonetim/toplu-randevu/", {
            "cihaz": self.cihaz.id,
            "tarih": self.ileri,
            "kullanici": self.hedef.id,
            "aralik": ["09:00-09:20", "10:00-10:30"],
        })
        self.assertEqual(Randevu.objects.filter(cihaz=self.cihaz, tarih=self.ileri).count(), 2)

    def test_dolu_aralik_atlanir(self):
        # 09:00-09:10 dolu olsun
        Randevu.objects.create(
            kullanici=self.hedef, cihaz=self.cihaz, tarih=self.ileri,
            baslangic_saati=time(9, 0), bitis_saati=time(9, 10), durum=Randevu.ONAYLANDI,
        )
        self.client.force_login(self.admin)
        self.client.post("/yonetim/toplu-randevu/", {
            "cihaz": self.cihaz.id,
            "tarih": self.ileri,
            "kullanici": self.hedef.id,
            "aralik": ["09:00-09:20", "10:00-10:20"],  # ilki çakışır -> atlanır, ikincisi oluşur
        })
        # Toplam 2 randevu: 1 önceden + 1 yeni (10:00-10:20); çakışan aralık atlandı
        self.assertEqual(Randevu.objects.filter(cihaz=self.cihaz, tarih=self.ileri).count(), 2)
