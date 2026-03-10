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

Quando il venv è attivo, nel prompt vedrai qualcosa tipo `(venv)` all’inizio della riga.

> **Importante (git):** la cartella `venv/` **non va mai pushata**.  
> Nel `.gitignore` assicurati di avere una riga `venv/`.

### 2. Installare le dipendenze da `requirements.txt`

Sul tuo ambiente di sviluppo principale, una volta che il progetto funziona, genera il file:

```bash
pip freeze > requirements.txt
```

Quando qualcuno clona il repo (o tu su un altro PC), dopo aver creato e attivato il `venv` esegue:

```bash
pip install -r requirements.txt
```

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

**Employee** – anagrafica dipendenti. Campi rilevanti: `first_name`, `last_name`, `email`, `birth_date`, `location`, `team`, `is_active`.  
Chi ha `is_active=false` compare tra i festeggiati ma non riceve email (è in ferie/assente).

**EmailConfig** – template email. Le migration creano automaticamente due record:

- `id=1` → email ai colleghi (non festeggiati)
- `id=2` → email personale al festeggiato

Placeholder supportati: `{date}`, `{employees}`, `{team}`, `{location}`, `{first_name}` (solo id=2).

**BirthdayNotification** – storico degli invii. Viene creato solo se ci sono festeggiati e almeno un'email viene inviata.

---

## Logica compleanni

Si considera festeggiato chi ha `birth_date.day == oggi.day` e `birth_date.month == oggi.month`.

Caso speciale: se oggi è **28 febbraio** e l'anno non è bisestile, vengono inclusi anche i nati il **29 febbraio**.

Le email vengono inviate solo ai dipendenti attivi che condividono **stessa location e stesso team** di almeno un festeggiato.

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

Per default le email vengono stampate in console, non inviate davvero:

```python
# core/settings.py
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
```

Fai la POST a `/api/notifications/sendToday/` e guarda il terminale del server.

---

## Dati di esempio (opzionale)

Crea `fixtures/sample_data.json` e caricala con:

```bash
venv\Scripts\python manage.py loaddata fixtures/sample_data.json
```

Esempio con 4 dipendenti (2 festeggiati stessa sede/team, 1 assente, 1 altra sede):

```json
[
  {
    "model": "api.employee",
    "pk": 1,
    "fields": {
      "first_name": "Luisa",
      "last_name": "Bianchi",
      "email": "luisa.bianchi@example.com",
      "birth_date": "1985-03-10",
      "location": "Milano",
      "team": "HR",
      "is_active": true
    }
  },
  {
    "model": "api.employee",
    "pk": 2,
    "fields": {
      "first_name": "Marco",
      "last_name": "Rossi",
      "email": "marco.rossi@example.com",
      "birth_date": "1990-03-10",
      "location": "Milano",
      "team": "HR",
      "is_active": true
    }
  },
  {
    "model": "api.employee",
    "pk": 3,
    "fields": {
      "first_name": "Anna",
      "last_name": "Neri",
      "email": "anna.neri@example.com",
      "birth_date": "1998-12-01",
      "location": "Milano",
      "team": "HR",
      "is_active": false
    }
  },
  {
    "model": "api.employee",
    "pk": 4,
    "fields": {
      "first_name": "Carlo",
      "last_name": "Verdi",
      "email": "carlo.verdi@example.com",
      "birth_date": "1992-07-21",
      "location": "Roma",
      "team": "IT",
      "is_active": true
    }
  }
]
```
