import calendar
import secrets

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.utils import timezone

from metadata_tool.models import AccountLifecycle


def add_months(value, months):
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


class Command(BaseCommand):
    help = "Send inactivity warnings and deactivate accounts after six months."

    def handle(self, *args, **options):
        now = timezone.now()
        warned = 0
        deactivated = 0
        accounts = AccountLifecycle.objects.filter(
            email_verified=True,
            deactivated_at__isnull=True,
        ).select_related("owner")

        for lifecycle in accounts.iterator():
            user = lifecycle.owner
            if user.is_staff or user.is_superuser:
                continue
            last_login = user.last_login or lifecycle.verified_at
            if last_login is None:
                continue

            warning_due = now >= add_months(last_login, 5)
            deactivation_due = now >= add_months(last_login, 6)

            if warning_due and lifecycle.warning_sent_at is None:
                sent = send_mail(
                    "Dein Bildarchiv-Konto wird bald deaktiviert",
                    f"Hallo {user.username},\n\nDu hast dich seit fünf Monaten nicht angemeldet. Wenn du dich nicht innerhalb des nächsten Monats anmeldest, wird dein Konto gesperrt. Deine Bilder bleiben erhalten und du erhältst dann einen Recovery-Code. Eine Anmeldung setzt die Frist zurück.",
                    None,
                    [user.email],
                    fail_silently=False,
                )
                if sent:
                    lifecycle.warning_sent_at = now
                    lifecycle.save(update_fields=["warning_sent_at"])
                    warned += 1

            if deactivation_due:
                recovery_code = secrets.token_urlsafe(12)
                sent = send_mail(
                    "Dein Bildarchiv-Konto wurde gesperrt",
                    f"Hallo {user.username},\n\nDein Konto wurde nach sechs Monaten ohne Anmeldung gesperrt. Deine Bilder bleiben erhalten.\n\nRecovery-Code: {recovery_code}\n\nMelde dich mit Benutzername und Passwort an und gib diesen Code im Feld Recovery-Code ein. Der Code ist einmalig.",
                    None,
                    [user.email],
                    fail_silently=False,
                )
                if sent:
                    lifecycle.recovery_code_hash = make_password(recovery_code)
                    lifecycle.deactivated_at = now
                    lifecycle.save(update_fields=["recovery_code_hash", "deactivated_at"])
                    user.is_active = False
                    user.save(update_fields=["is_active"])
                    deactivated += 1

        self.stdout.write(self.style.SUCCESS(f"Warnungen versendet: {warned}; Konten gesperrt: {deactivated}"))