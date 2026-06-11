# Veri migration'ı: Otomatik onay iş kuralına geçişte, hâlâ "onay bekleniyor"
# durumunda bekleyen mevcut randevuları "onaylandı" durumuna taşır.
from django.db import migrations


def onay_bekleyenleri_onayla(apps, schema_editor):
    Randevu = apps.get_model("rezervasyon", "Randevu")
    Randevu.objects.filter(durum="onay_bekleniyor").update(durum="onaylandi")


def geri_al(apps, schema_editor):
    # Geri dönüş güvenli değil (hangi randevunun gerçekten beklediğini bilemeyiz),
    # bu yüzden no-op bırakılır.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("rezervasyon", "0017_alter_randevu_durum"),
    ]

    operations = [
        migrations.RunPython(onay_bekleyenleri_onayla, geri_al),
    ]
