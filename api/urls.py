from django.urls import path

from .views import (
    BirthdayNotificationListView,
    EmailConfigDetailView,
    EmailConfigListCreateView,
    EmployeeDetailView,
    EmployeeListCreateView,
    TodayBirthdayEmployeeListView,
    ping,
    send_today_birthdays,
)

urlpatterns = [
    # Healthcheck
    path("ping/", ping, name="ping"),

    # =======================
    #  EMPLOYEES (DIPENDENTI)
    # =======================

    # Lista tutti i dipendenti (GET)
    path(
        "employees/getEmployees/",
        EmployeeListCreateView.as_view(),
        name="employees-get",
    ),
    # Crea un nuovo dipendente (POST)
    path(
        "employees/createEmployee/",
        EmployeeListCreateView.as_view(),
        name="employees-create",
    ),
    # Dettaglio di un dipendente (GET)
    path(
        "employees/getEmployee/<int:pk>/",
        EmployeeDetailView.as_view(),
        name="employee-get",
    ),
    # Aggiorna un dipendente (PUT/PATCH)
    path(
        "employees/updateEmployee/<int:pk>/",
        EmployeeDetailView.as_view(),
        name="employee-update",
    ),
    # Cancella un dipendente (DELETE)
    path(
        "employees/deleteEmployee/<int:pk>/",
        EmployeeDetailView.as_view(),
        name="employee-delete",
    ),
    # Dipendenti che compiono gli anni oggi (GET)
    path(
        "employees/getTodayBirthdays/",
        TodayBirthdayEmployeeListView.as_view(),
        name="employees-today-birthdays",
    ),

    # ======================================
    #  NOTIFICHE COMPLEANNI (INVIO/STORICO)
    # ======================================

    # Trigger invio email compleanni di oggi (POST)
    path(
        "notifications/sendToday/",
        send_today_birthdays,
        name="notifications-send-today",
    ),
    # Storico notifiche inviate (GET)
    path(
        "notifications/getNotifications/",
        BirthdayNotificationListView.as_view(),
        name="notifications-get",
    ),

    # =======================
    #  CONFIGURAZIONE EMAIL
    # =======================

    # Lista/creazione config email
    path(
        "config/email/",
        EmailConfigListCreateView.as_view(),
        name="email-config-list-create",
    ),
    # Dettaglio/modifica/svuota singola config email
    path(
        "config/email/<int:pk>/",
        EmailConfigDetailView.as_view(),
        name="email-config-detail",
    ),
]
