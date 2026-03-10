from datetime import date
import calendar

from django.db.models import Q
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import BirthdayNotification, EmailConfig, Employee
from .serializers import (
    BirthdayNotificationSerializer,
    EmailConfigSerializer,
    EmployeeSerializer,
)
from .tasks import send_today_birthdays_task


@api_view(["GET"])
def ping(request):
    return Response({"message": "Ciao dal backend Django!"})


class EmployeeListCreateView(generics.ListCreateAPIView):
    """
    - GET: lista dipendenti (con filtri base)
    - POST: crea nuovo dipendente
    """

    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            if is_active.lower() in {"true", "1"}:
                qs = qs.filter(is_active=True)
            elif is_active.lower() in {"false", "0"}:
                qs = qs.filter(is_active=False)
        return qs


class EmployeeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    - GET: dettaglio dipendente
    - PUT/PATCH: aggiornamento dati (email, data di nascita, ecc.)
    - DELETE: eventuale cancellazione (per MVP puoi anche non usarlo)
    """

    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer


class TodayBirthdayEmployeeListView(generics.ListAPIView):
    """
    Restituisce solo i dipendenti che compiono gli anni oggi.
    """

    serializer_class = EmployeeSerializer

    def get_queryset(self):
        today = date.today()
        # Come nel task: includiamo anche chi non è attivo (verrà marcato come assente),
        # così da avere un quadro completo dei festeggiati del giorno.
        filters = Q(
            birth_date__month=today.month,
            birth_date__day=today.day,
        )
        if today.month == 2 and today.day == 28 and not calendar.isleap(today.year):
            filters |= Q(birth_date__month=2, birth_date__day=29)
        return Employee.objects.filter(filters)


class BirthdayNotificationListView(generics.ListAPIView):
    """
    Storico degli invii effettuati.
    """

    queryset = BirthdayNotification.objects.all()
    serializer_class = BirthdayNotificationSerializer


class EmailConfigListCreateView(generics.ListCreateAPIView):
    """
    GET: lista di tutte le email config (non festeggiati, festeggiati, ecc.)
    POST: crea una nuova configurazione.
    """

    queryset = EmailConfig.objects.all()
    serializer_class = EmailConfigSerializer


class EmailConfigDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: dettaglio config (per id)
    PUT/PATCH: aggiorna config
    DELETE: cancella config (se non referenziata altrove)
    """

    queryset = EmailConfig.objects.all()
    serializer_class = EmailConfigSerializer


@api_view(["POST"])
def send_today_birthdays(request):
    """
    Endpoint manuale da chiamare (es. via Postman) per:
    - enqueue di un Task del Django Task Framework che:
      - identifica i dipendenti che compiono gli anni oggi
      - invia un'email riepilogativa
      - salva un record nello storico degli invii
    """

    exclude_birthday = request.query_params.get("exclude_birthday", "true").lower() in {
        "true",
        "1",
        "yes",
    }

    result = send_today_birthdays_task.enqueue(
        exclude_birthday_people=exclude_birthday,
    )
    return Response(
        {
            "detail": "Task di invio compleanni enqueued.",
            "result_id": result.id,
        },
        status=status.HTTP_202_ACCEPTED,
    )

