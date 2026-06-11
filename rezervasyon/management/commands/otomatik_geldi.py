# TURKCE ARAMA: otomatik geldi, 48 saat, cron, zamanlanmis gorev
#
# Kullanim (ornek cron / zamanlanmis gorev):
#   python manage.py otomatik_geldi
#
# Bitiminden OTOMATIK_GELDI_SURESI_SAAT (varsayilan 48) saatten fazla gecmis
# ve hala "onaylandi" durumunda kalan randevulari "geldi" yapar.
#
# NOT: Ayni mantik liste/yonetim sayfalari acildiginda da (lazy) calisir;
# bu komut, kullanici hic sayfa acmasa bile durumlarin guncel kalmasini saglar.

from django.core.management.base import BaseCommand

from rezervasyon.view_helpers import otomatik_geldi_isaretle


class Command(BaseCommand):
    help = "48 saat gecmis onayli randevulari otomatik 'geldi' olarak isaretler."

    def handle(self, *args, **options):
        guncellenen = otomatik_geldi_isaretle()
        self.stdout.write(
            self.style.SUCCESS(f"{guncellenen} randevu otomatik 'geldi' olarak isaretlendi.")
        )
