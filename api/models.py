from django.db import models


class Employee(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    birth_date = models.DateField()
    location = models.CharField(max_length=100, blank=True)  # sede
    team = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"


class BirthdayNotification(models.Model):
    """
    Rappresenta un invio giornaliero di email con i compleanni.
    """

    sent_at = models.DateTimeField(auto_now_add=True)
    subject = models.CharField(max_length=255)
    body_preview = models.TextField(help_text="Prime righe dell'email inviata")
    recipients = models.TextField(
        help_text="Lista indirizzi email destinatari (separati da virgola)"
    )
    birthday_employees = models.ManyToManyField(
        Employee, related_name="birthday_notifications"
    )
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self) -> str:
        return f"Notifica compleanni del {self.sent_at.date()}"


class EmailConfig(models.Model):
    """
    Configurazione per template email e impostazioni base del servizio.
    Puoi usare più record distinti (es. uno per chi NON festeggia,
    uno per chi festeggia) e referenziarli per id nella logica applicativa.
    """

    subject_template = models.CharField(
        max_length=255,
        default="Festeggiati di oggi - {date}",
    )
    body_template = models.TextField(
        default=(
            "Buongiorno,\n\n"
            "Ecco chi compie gli anni oggi:\n"
            "{employees}\n\n"
            "Fai loro gli auguri!"
        ),
        help_text="Template testo email. Usa {employees} e {date} come placeholder.",
    )
    sender_email = models.EmailField(
        blank=True,
        help_text="Indirizzo mittente. Se vuoto, viene usato DEFAULT_FROM_EMAIL.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Email config"
        verbose_name_plural = "Email configs"

    def __str__(self) -> str:
        return "Configurazione email"


