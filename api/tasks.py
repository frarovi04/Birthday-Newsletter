from datetime import date
import calendar
import json

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.tasks import task

from .models import BirthdayNotification, EmailConfig, Employee


def _employees_text_list(employees):
    """
    Restituisce le righe 'nome cognome: N anni' per l'elenco festeggiati.
    Se un dipendente non è attivo (is_active=False) viene marcato come assente/in ferie.
    """
    today = date.today()
    lines = []
    for emp in employees:
        age = today.year - emp.birth_date.year
        has_had_birthday = (today.month, today.day) >= (
            emp.birth_date.month,
            emp.birth_date.day,
        )
        if not has_had_birthday:
            age -= 1
        status_note = ""
        if not emp.is_active:
            status_note = " (assente/in ferie, fagli gli auguri al ritorno)"
        lines.append(f"- {emp.first_name} {emp.last_name}: {age} anni{status_note}")
    return "\n".join(lines) if lines else "Nessuno."


def _build_daily_email(employees):
    """
    Costruisce subject e body dell'email usando il template in EmailConfig (api/config/email).
    Placeholder supportati: {date}, {employees}, {team}, {location}.
    Se non c'è config o template vuoti, usa valori di default.
    """
    today = date.today()
    date_str = today.strftime("%d/%m/%Y")
    employees_str = _employees_text_list(employees) if employees else "Nessuno."

    teams = sorted({e.team for e in employees if getattr(e, "team", None)})
    locations = sorted({e.location for e in employees if getattr(e, "location", None)})
    team_str = ", ".join(teams) if teams else ""
    location_str = ", ".join(locations) if locations else ""

    config = None
    try:
        config = EmailConfig.objects.filter(pk=1).first()
    except Exception:
        pass

    if config and (config.subject_template or config.body_template):
        subject_template = config.subject_template or "Compleanni di oggi"
        body_template = (
            config.body_template or "Oggi non ci sono compleanni nel team {team} di {location}."
        )
        subject = subject_template.format(
            date=date_str,
            employees=employees_str,
            team=team_str,
            location=location_str,
        )
        body = body_template.format(
            date=date_str,
            employees=employees_str,
            team=team_str,
            location=location_str,
        )
        return subject, body

    # Fallback senza config
    if not employees:
        return "Compleanni di oggi", "Oggi non ci sono compleanni nel team {team} di {location}."
    subject = f"Festeggiati di oggi - {date_str}"
    body = (
        "Buongiorno,\n\nEcco chi compie gli anni oggi:\n"
        f"{employees_str}\n\nFai loro gli auguri! 🥳"
    )
    return subject, body


@task()
def send_today_birthdays_task(
    exclude_birthday_people: bool = True,
) -> int:
    """
    Task che:
    - trova i dipendenti che compiono gli anni oggi
    - invia l'email (usando EMAIL_BACKEND configurato, es. console)
    - salva una BirthdayNotification

    Ritorna l'id della notifica creata.
    """
    today = date.today()

    # Gestione compleanni: include il 29/02 il 28/02 negli anni non bisestili.
    # Non filtriamo su is_active qui, così anche i dipendenti non attivi
    # compaiono nella lista festeggiati (marcati come assenti), ma non ricevono email.
    filters = Q(
        birth_date__month=today.month,
        birth_date__day=today.day,
    )
    if today.month == 2 and today.day == 28 and not calendar.isleap(today.year):
        filters |= Q(birth_date__month=2, birth_date__day=29)

    birthday_employees_qs = Employee.objects.filter(filters)
    birthday_employees = list(birthday_employees_qs)

    # Se oggi non ci sono compleanni non facciamo nulla: nessuna mail, nessuna notifica.
    if not birthday_employees:
        return 0

    subject, body = _build_daily_email(birthday_employees)

    recipients_qs = Employee.objects.filter(is_active=True).exclude(email="")

    # Invio solo a persone dello stesso team e stessa sede
    # dei festeggiati di oggi.
    locations = {e.location for e in birthday_employees if e.location}
    teams = {e.team for e in birthday_employees if e.team}
    if locations:
        recipients_qs = recipients_qs.filter(location__in=locations)
    if teams:
        recipients_qs = recipients_qs.filter(team__in=teams)

    birthday_ids = [emp.pk for emp in birthday_employees]

    # Gruppo 1: colleghi che NON festeggiano oggi
    non_birthday_qs = recipients_qs
    if exclude_birthday_people and birthday_employees:
        non_birthday_qs = non_birthday_qs.exclude(pk__in=birthday_ids)
    non_birthday_emails = sorted({emp.email for emp in non_birthday_qs})

    # Gruppo 2: persone che festeggiano oggi (solo quelle con email valorizzata)
    birthday_recipients = [
        emp for emp in birthday_employees if emp.email and emp.is_active
    ]

    success = True
    error_message = ""

    # Costruisco un JSON riepilogativo di cosa verrà inviato
    payload = {
        "subject": subject,
        "body": body,
        "recipients_non_birthday": non_birthday_emails,
        "recipients_birthday": [e.email for e in birthday_recipients],
        "birthday_people": [
            {
                "id": e.id,
                "first_name": e.first_name,
                "last_name": e.last_name,
                "email": e.email,
                "location": e.location,
                "team": e.team,
                "birth_date": e.birth_date.isoformat(),
            }
            for e in birthday_employees
        ],
    }
    print("=== BirthdayNewsletter sendToday payload ===")
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
    # Config 1: non festeggiati (usata in _build_daily_email)
    config = EmailConfig.objects.filter(pk=1).first()
    # Config 2: festeggiati (DEVE esistere, niente fallback)
    birthday_cfg = EmailConfig.objects.filter(pk=2).first()
    if not config or not birthday_cfg:
        raise RuntimeError(
            "EmailConfig mancante: assicurati di avere pk=1 (non festeggiati) "
            "e pk=2 (festeggiati) configurati a DB."
        )
    if config.sender_email:
        from_email = config.sender_email

    # Invio a chi NON festeggia: un'unica email con la lista festeggiati

    if non_birthday_emails:
        try:
            send_mail(
                subject=subject,
                message=non_birthday_body,
                from_email=from_email,
                recipient_list=non_birthday_emails,
                fail_silently=False,
            )
        except Exception as exc:
            success = False
            error_message = str(exc)

    # Invio a chi festeggia: email personalizzata con auguri + (eventuale) lista
    for emp in birthday_recipients:
        # Lista di eventuali altri festeggiati (escludendo il diretto interessato)
        other_birthday_people = [e for e in birthday_employees if e.pk != emp.pk]

        # Usa SEMPRE la config dedicata ai festeggiati (pk=2)
        today = date.today()
        date_str = today.strftime("%d/%m/%Y")
        employees_str = (
            _employees_text_list(other_birthday_people) if other_birthday_people else "Nessuno."
        )
        teams = sorted(
            {e.team for e in birthday_employees if getattr(e, "team", None)}
        )
        locations = sorted(
            {e.location for e in birthday_employees if getattr(e, "location", None)}
        )
        team_str = ", ".join(teams) if teams else ""
        location_str = ", ".join(locations) if locations else ""

        personal_subject = birthday_cfg.subject_template.format(
            date=date_str,
            employees=employees_str,
            team=team_str,
            location=location_str,
            first_name=emp.first_name,
        )
        personal_body = birthday_cfg.body_template.format(
            date=date_str,
            employees=employees_str,
            team=team_str,
            location=location_str,
            first_name=emp.first_name,
        )
        try:
            send_mail(
                subject=personal_subject,
                message=personal_body,
                from_email=from_email,
                recipient_list=[emp.email],
                fail_silently=False,
            )
        except Exception as exc:
            success = False
            error_message = str(exc)

    recipients_str = ", ".join(non_birthday_emails + [e.email for e in birthday_recipients])

    with transaction.atomic():
        notification = BirthdayNotification.objects.create(
            subject=subject,
            body_preview=body[:1000],
            recipients=recipients_str,
            success=success,
            error_message=error_message,
        )
        if birthday_employees:
            notification.birthday_employees.set(birthday_employees)

    return notification.id

