## Birthday Newsletter – Backend Django (solo API)

Backend Django per inviare una newsletter quotidiana con i compleanni dei dipendenti.  
Non c’è interfaccia grafica: si usa tramite strumenti come Postman o curl.

---

## 1. Requisiti

- Python 3.12+
- Virtualenv già creato in `BirthdayNewsletter-BE/venv`
- SQLite (database di default di Django)
- Postman o equivalente per chiamare le API

---

## 2. Avvio del progetto

Da terminale:

```bash
cd "BirthdayNewsletter-BE"
venv\Scripts\python manage.py migrate
venv\Scripts\python manage.py runserver
```

L’API sarà disponibile su `http://127.0.0.1:8000`.

**Healthcheck rapido**

- **GET** `http://127.0.0.1:8000/api/ping/`  
  Risposta attesa:
  ```json
  { "message": "Ciao dal backend Django!" }
  ```

---

## 3. Modello dati e logiche di business

### 3.1 Employee (anagrafica dipendenti)

Campi principali:

- `first_name`, `last_name`
- `email` (univoca, usata per inviare le mail)
- `birth_date` (formato `AAAA-MM-GG`)
- `location` (sede, es. "Milano")
- `team` (es. "HR", "IT")
- `is_active`:
  - `true` → dipendente attivo (presente, riceve le mail)
  - `false` → dipendente assente/in ferie:
    - viene comunque riportato nella lista festeggiati,
    - ma **non riceve email**.

Altre info:

- `created_at`, `updated_at`
- Ordinamento di default: per `last_name`, poi `first_name`.

### 3.2 BirthdayNotification (storico invii)

Ogni volta che viene inviato il riepilogo compleanni (e ci sono festeggiati) viene creata una `BirthdayNotification`:

- `sent_at`
- `subject`
- `body_preview` (prime ~1000 lettere dell’email di team)
- `recipients` (stringa con email separate da virgola)
- `birthday_employees` (ManyToMany con gli `Employee` festeggiati)
- `success` (bool)
- `error_message` (eventuale errore SMTP)

### 3.3 EmailConfig (template email)

La tabella `EmailConfig` contiene i template email e il mittente.  
Le migration iniziali creano automaticamente due record:

- **id = 1** → template per chi **NON** festeggia  
- **id = 2** → template per chi **festeggia**

Campi:

- `subject_template`
- `body_template`
- `sender_email` (se vuoto, usa `DEFAULT_FROM_EMAIL` dalle settings)

**Placeholder supportati** nei template:

- `{date}` → data di oggi (es. `10/03/2026`)
- `{employees}` → elenco festeggiati in forma:
  - `- Nome Cognome: N anni`
  - se `is_active=false`:  
    `- Nome Cognome: N anni (assente/in ferie, fagli gli auguri al ritorno)`
- `{team}` → elenco team coinvolti (es. `HR, IT`)
- `{location}` → elenco sedi coinvolte (es. `Milano, Roma`)
- `{first_name}` → nome del festeggiato (solo per il template dei festeggiati)

---

## 4. Logica compleanni (business)

### 4.1 Individuazione del compleanno

Viene considerato festeggiato chi:

- ha `birth_date.month == oggi.month`
- e `birth_date.day == oggi.day`

**Caso speciale 29 febbraio**

- se l’anno **non è bisestile**, il 29/02 non esiste;
- il **28/02**, oltre a chi è nato il 28/02, vengono considerati festeggiati anche i nati il **29/02**.

### 4.2 Chi viene contato come festeggiato

- Tutti gli `Employee` con `birth_date` corrispondente, indipendentemente da `is_active`.
- Chi ha `is_active=false`:
  - compare comunque nel placeholder `{employees}`,
  - marcato come "assente/in ferie, fagli gli auguri al ritorno",
  - **non riceve email**.

### 4.3 A chi vengono inviate le email

Vengono considerati destinatari solo i dipendenti che:

- hanno `is_active=true`,
- hanno `email` non vuota,
- condividono **stessa `location` e stesso `team`** di almeno un festeggiato del giorno.

La newsletter è quindi "per team e sede" dei festeggiati.

---

## 5. Configurazione template email via API

Base URL: `http://127.0.0.1:8000/api`

### 5.1 Endpoint EmailConfig

- **GET** `/config/email/` → lista di tutte le config
- **POST** `/config/email/` → crea una nuova config
- **GET** `/config/email/<id>/` → dettaglio
- **PUT/PATCH** `/config/email/<id>/` → modifica
- **DELETE** `/config/email/<id>/` → elimina

### 5.2 Config di base (id 1 e 2)

**Config 1 – non festeggiati (id = 1)**  
Usata per le email ai **colleghi che NON festeggiano** ma appartengono ai team/sedi dei festeggiati:

```json
{
  "subject_template": "Compleanni del team {team} di {location} - {date}",
  "body_template": "Buongiorno team {team} di {location},\n\nEcco chi compie gli anni oggi:\n{employees}\n\nFai loro gli auguri!",
  "sender_email": "no-reply@birthdaynewsletter.com"
}
```

**Config 2 – festeggiati (id = 2)**  
Usata per le email ai **festeggiati**:

```json
{
  "subject_template": "Buon compleanno {first_name}!",
  "body_template": "Ciao {first_name},\n\ntanti auguri di buon compleanno!\n\nNel team {team} di {location} festeggiano anche:\n{employees}\n\nGoditi la giornata!",
  "sender_email": "no-reply@birthdaynewsletter.com"
}
```

Le migration creano automaticamente questi 2 record.  
Il task richiede che `id=1` e `id=2` esistano.

---

## 6. Logica completa degli invii (Task Framework Django)

Il task principale è `send_today_birthdays_task` (Django 6 – Tasks Framework).

### 6.1 Flusso generale

1. **Trova i festeggiati di oggi**
   - applica la regola del 29/02,
   - include anche i non attivi (solo per la lista `{employees}`).

2. **Se non ci sono festeggiati oggi**
   - il task termina subito (`return 0`),
   - **non invia email**,
   - **non crea `BirthdayNotification`**.

3. **Calcola i destinatari**
   - parte da tutti gli `Employee` attivi con email,
   - filtra per stessa `location` e `team` dei festeggiati,
   - separa:
     - `non_birthday_emails` → colleghi che non compiono gli anni,
     - `birthday_recipients` → festeggiati attivi con email.

4. **Costruisce i testi**

   - **Per chi NON festeggia**:
     - usa `EmailConfig` con `id = 1`,
     - calcola `subject` e `body` applicando il template con `{date}`, `{employees}`, `{team}`, `{location}`,
     - `{employees}` contiene tutti i festeggiati (attivi e non).

   - **Per chi festeggia**:
     - usa `EmailConfig` con `id = 2`,
     - per ogni festeggiato:
       - calcola `{employees}` con gli altri festeggiati (esclude il diretto interessato),
       - genera `subject` e `body` specifici usando anche `{first_name}`.

5. **Invio**

   - **Non festeggiati**:
     - per ogni email in `non_birthday_emails`:
       - invia una mail separata con `subject`/`body` di team.
   - **Festeggiati**:
     - per ogni `birthday_recipients`:
       - invia una mail personale con il template id=2.

6. **Storico**

   - Se qualche mail è stata inviata:
     - crea una `BirthdayNotification` con:
       - `subject` (quello usato per i non festeggiati),
       - `body_preview` (corpo di team tagliato),
       - `recipients` (tutti gli indirizzi coinvolti),
       - collegamento ai `birthday_employees`,
       - `success` / `error_message`.

---

## 7. Endpoint REST (riepilogo)

Base URL: `http://127.0.0.1:8000/api`

### 7.1 Dipendenti

- **Crea dipendente**
  - `POST /employees/createEmployee/`
  - Body (esempio):
    ```json
    {
      "first_name": "Luisa",
      "last_name": "Bianchi",
      "email": "luisa.bianchi@example.com",
      "birth_date": "1985-03-10",
      "location": "Milano",
      "team": "HR",
      "is_active": true
    }
    ```

- **Lista dipendenti**
  - `GET /employees/getEmployees/`
  - Query param: `?is_active=true|false` (opzionale)

- **Dettaglio / update / delete**
  - `GET /employees/getEmployee/<id>/`
  - `PUT/PATCH /employees/updateEmployee/<id>/`
  - `DELETE /employees/deleteEmployee/<id>/`

- **Festeggiati di oggi**
  - `GET /employees/getTodayBirthdays/`
  - Restituisce tutti i festeggiati (anche `is_active=false`).

### 7.2 Invio compleanni

- **Trigger manuale invio**
  - `POST /notifications/sendToday/`
  - Query opzionale: `?exclude_birthday=false` per includere i festeggiati anche tra i destinatari di team (default: `true`).

### 7.3 Storico invii

- **Lista invii**
  - `GET /notifications/getNotifications/`
  - Restituisce la lista di `BirthdayNotification` ordinate dalla più recente.

### 7.4 Config email

- `GET /config/email/` → lista config
- `POST /config/email/` → crea config
- `GET /config/email/<id>/` → dettaglio
- `PUT/PATCH /config/email/<id>/` → modifica
- `DELETE /config/email/<id>/` → elimina

---

## 8. Esempi di chiamate API (curl)

Tutti gli esempi assumono che il server giri su `http://127.0.0.1:8000`.

### 8.1 Healthcheck

```bash
curl -X GET http://127.0.0.1:8000/api/ping/
```

### 8.2 Creazione dipendente

```bash
curl -X POST http://127.0.0.1:8000/api/employees/createEmployee/ ^
  -H "Content-Type: application/json" ^
  -d "{
        \"first_name\": \"Luisa\",
        \"last_name\": \"Bianchi\",
        \"email\": \"luisa.bianchi@example.com\",
        \"birth_date\": \"1985-03-10\",
        \"location\": \"Milano\",
        \"team\": \"HR\",
        \"is_active\": true
      }"
```

### 8.3 Lista dipendenti attivi

```bash
curl -X GET "http://127.0.0.1:8000/api/employees/getEmployees/?is_active=true"
```

### 8.4 Festeggiati di oggi

```bash
curl -X GET http://127.0.0.1:8000/api/employees/getTodayBirthdays/
```

### 8.5 Invio manuale newsletter compleanni

```bash
curl -X POST http://127.0.0.1:8000/api/notifications/sendToday/
```

Oppure, per includere anche i festeggiati tra i destinatari di team:

```bash
curl -X POST "http://127.0.0.1:8000/api/notifications/sendToday/?exclude_birthday=false"
```

### 8.6 Storico invii

```bash
curl -X GET http://127.0.0.1:8000/api/notifications/getNotifications/
```

### 8.7 Configurazioni email

```bash
curl -X GET http://127.0.0.1:8000/api/config/email/
```

---

## 9. Come testare l'invio email

Nel file `core/settings.py` l’email backend è impostato così:

```python
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "no-reply@birthdaynewsletter.com"
```

Questo significa che:

- le email **non vengono spedite realmente** verso un server SMTP,
- ogni invio viene stampato in **console**, nella finestra dove hai lanciato:

```bash
venv\Scripts\python manage.py runserver
```

Per vedere le email:

1. Avvia il server Django.
2. Esegui una chiamata POST a `/api/notifications/sendToday/` (da Postman o curl).
3. Guarda il terminale: per ogni destinatario vedrai un blocco con:
   - header (`Subject`, `From`, `To`, ecc.),
   - body dell’email in chiaro.

---

## 10. Dati di esempio (fixture opzionale)

Se vuoi popolare rapidamente il database con dati demo, puoi usare una fixture Django.  
Creala nella cartella `BirthdayNewsletter-BE/fixtures/sample_data.json` con un contenuto simile a questo:

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

Poi, da `BirthdayNewsletter-BE`:

```bash
venv\Scripts\python manage.py loaddata fixtures/sample_data.json
```

Questo comando crea 4 dipendenti di esempio:

- due festeggiati nello stesso team/sede (Luisa e Marco, HR Milano),
- una collega assente/in ferie (Anna),
- un dipendente in altra sede/team (Carlo).

Le `EmailConfig` di base (id 1 e 2) vengono invece create automaticamente dalla migration `0003_seed_emailconfig_defaults`, quindi non è necessario inserirle nella fixture.
