# Birthday Newsletter – Backend Django

Backend solo API (niente interfaccia) per inviare una newsletter giornaliera con i compleanni dei dipendenti.

---

## Setup

### 1. Creare e attivare il virtualenv (solo la prima volta su una macchina)

```bash
cd BirthdayNewsletter-BE
python -m venv venv
```

**Attivazione del venv:**

- **Windows PowerShell (consigliato)**

  ```bash
  .\venv\Scripts\Activate.ps1
  ```

- **Windows CMD classico**

  ```cmd
  venv\Scripts\activate.bat
  ```

- **Git Bash / WSL / macOS / Linux**
  ```bash
  source venv/bin/activate
  ```

Nel gitignore assicurati di avere una riga venv/.

### 3. Migrazioni e avvio server

Con il virtualenv attivo:

```bash
python manage.py migrate
python manage.py runserver
```

### 4. Disattivare il virtualenv

Quando hai finito di lavorare sul progetto, puoi uscire dal venv con:

```bash
deactivate
```

### 5. Rifare il venv su un nuovo PC (o se si rompe)

Se cloni il repo su un’altra macchina (o vuoi ripartire da zero):

```bash
cd BirthdayNewsletter-BE
python -m venv venv

# attiva il venv (vedi punto 1)

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Server su `http://127.0.0.1:8000`. Per verificare che giri:

```bash
curl http://127.0.0.1:8000/api/ping/
# { "message": "Ciao dal backend Django!" }
```

---

## Modelli

**Employee** – anagrafica dipendenti. Campi:
`first_name`,
`last_name`,
`email`,
`birth_date`,
`location`,
`team`,
`is_active`. ì

Chi ha `is_active=false` compare tra i festeggiati ma non riceve email (è in ferie/assente), chi deve fargli gli auguri riceverà una mail con scritto di farglieli una volta tornato.

**EmailConfig** – template email. Le migration creano automaticamente due record:

- `id=1` → email ai colleghi (non festeggiati)
- `id=2` → email personale al festeggiato

Placeholder supportati: `{date}`, `{employees}`, `{team}`, `{location}`, `{first_name}` (solo id=2).

**BirthdayNotification** – storico degli invii. Viene creato solo se ci sono festeggiati e almeno un'email viene inviata.

---

## Logica compleanni

Si considera festeggiato chi ha `birth_date.day == oggi.day` e `birth_date.month == oggi.month`.

Caso speciale: se è il 28 febbraio e l'anno non è bisestile, vengono inclusi anche i nati il 29 febbraio.

Le email vengono inviate solo ai dipendenti attivi che condividono stessa sede e stesso team di almeno un festeggiato.

- I dipendenti non festeggiati ricevono un'unica email di team con la lista di tutti i festeggiati filtrata per sede e team.
- Ogni festeggiato riceve una mail personale che mostra auguri e in caso ci siano, altri festeggiati nella sua stessa sede e team.

---

## Endpoint principali

```
# Dipendenti
POST   /api/employees/createEmployee/
GET    /api/employees/getEmployees/?is_active=true
GET    /api/employees/getEmployee/<id>/
PUT    /api/employees/updateEmployee/<id>/
DELETE /api/employees/deleteEmployee/<id>/
GET    /api/employees/getTodayBirthdays/

# Invio newsletter
POST   /api/notifications/sendToday/
GET    /api/notifications/getNotifications/

# Template email
GET/POST        /api/config/email/
GET/PUT/DELETE  /api/config/email/<id>/
```

Parametro opzionale per l'invio: `?exclude_birthday=false` per mandare la mail di team anche ai festeggiati (default: `true`).

---

## Test email

Le mail sono unicamente stampate in console, non utilizzando credenziali smtp reali:

```python
# core/settings.py
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
```

Fai la POST a `/api/notifications/sendToday/` e guarda il terminale del server.

---

## Dati di esempio (opzionale)

Esempio con alcuni dipendenti (2 festeggiati stessa sede/team, 1 assente, 1 altra sede).  
Ho utilizzato questo Json in body su postman, chiamando piu volte `POST /api/employees/createEmployee/` (un oggetto alla volta):

```json
[
  {
    "first_name": "Luisa",
    "last_name": "Bianchi",
    "email": "luisa.bianchi@example.com",
    "birth_date": "1985-03-10",
    "location": "Milano",
    "team": "HR",
    "is_active": true
  },
  {
    "first_name": "Marco",
    "last_name": "Rossi",
    "email": "marco.rossi@example.com",
    "birth_date": "1990-03-10",
    "location": "Milano",
    "team": "HR",
    "is_active": true
  },
  {
    "first_name": "Anna",
    "last_name": "Neri",
    "email": "anna.neri@example.com",
    "birth_date": "1998-12-01",
    "location": "Milano",
    "team": "HR",
    "is_active": false
  },
  {
    "first_name": "Carlo",
    "last_name": "Verdi",
    "email": "carlo.verdi@example.com",
    "birth_date": "1992-07-21",
    "location": "Roma",
    "team": "IT",
    "is_active": true
  },
  {
    "first_name": "Giulia",
    "last_name": "Blu",
    "email": "giulia.blu@example.com",
    "birth_date": "1996-02-29",
    "location": "Milano",
    "team": "HR",
    "is_active": true
  }
]
```
