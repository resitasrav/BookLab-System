# Veri migration'ı: Mevcut randevuların başlangıç/bitiş saatlerini en yakın
# 10 dakikalık dilime yuvarlar (ör. 09:07 -> 09:10). Düzensiz dakika değerlerini
# 10 dk slot standardına getirir.
#
# GÜVENLİK: Yuvarlama sonrası başlangıç >= bitiş olacaksa o kayda dokunulmaz
# (sıfır/negatif süreli randevu oluşmasın).
from datetime import time

from django.db import migrations


def _yuvarla(t):
    """time nesnesini en yakın 10 dakikaya yuvarlar; 23:50'de kapanır."""
    toplam = t.hour * 60 + t.minute
    toplam = round(toplam / 10) * 10
    toplam = min(toplam, 23 * 60 + 50)  # geçerli TimeField aralığında kal
    return time(toplam // 60, toplam % 60)


def saatleri_yuvarla(apps, schema_editor):
    Randevu = apps.get_model("rezervasyon", "Randevu")
    guncellenecek = []
    # Yalnızca dakikası 10'un katı olmayan kayıtları tara.
    for r in Randevu.objects.only("id", "baslangic_saati", "bitis_saati").iterator():
        b, e = r.baslangic_saati, r.bitis_saati
        if b.minute % 10 == 0 and e.minute % 10 == 0:
            continue
        yb, ye = _yuvarla(b), _yuvarla(e)
        if yb >= ye:
            continue  # güvenlik: geçersiz aralık oluşturma
        r.baslangic_saati, r.bitis_saati = yb, ye
        guncellenecek.append(r)

    # Toplu güncelle (bulk_update, save()/clean() tetiklemez — migrationda istenen budur).
    if guncellenecek:
        Randevu.objects.bulk_update(guncellenecek, ["baslangic_saati", "bitis_saati"], batch_size=200)


def geri_al(apps, schema_editor):
    # Orijinal dakikalar bilinemez; geri dönüş no-op.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("rezervasyon", "0018_mevcut_randevulari_onayla"),
    ]

    operations = [
        migrations.RunPython(saatleri_yuvarla, geri_al),
    ]
