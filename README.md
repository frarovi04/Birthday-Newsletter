# Birthday Newsletter – Backend Django

Backend solo API (niente interfaccia) per inviare una newsletter giornaliera con i compleanni dei dipendenti.

---

## Setup rapido

Da dentro la cartella `BirthdayNewsletter`:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Il server parte su `http://127.0.0.1:8000`. Per verificare che giri:

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
`is_active`.

Chi ha `is_active=false` compare tra i festeggiati ma non riceve email (è in ferie/assente), chi deve fargli gli auguri riceverà una mail con scritto di farglieli una volta tornato.

**EmailConfig** – template email. Le migration creano automaticamente due record:

- `id=1` → email ai colleghi (non festeggiati)
- `id=2` → email personale al festeggiato

Placeholder supportati: `{date}`, `{employees}`, `{team}`, `{location}`, `{first_name}` (solo id=2).

**BirthdayNotification** – storico degli invii. Viene creato solo se ci sono festeggiati e almeno un'email viene inviata.

---

## Logiche di business

Chi è “festeggiato”

Un dipendente è considerato festeggiato se il giorno e il mese di nascita coincidono con la data di oggi.  
Per chi è nato il 29 febbraio, negli anni non bisestili il compleanno viene considerato il 28 febbraio.

### Chi riceve le email

Le email partono solo verso dipendenti attivi che condividono sede e team con almeno un festeggiato.

Per ogni combinazione sede–team succede questo:

- i colleghi non festeggiati ricevono una sola email di team con la lista dei festeggiati di quella sede e di quel team;
- ogni festeggiato riceve una mail personale, che può includere anche gli altri festeggiati della stessa sede e dello stesso team;
- se un festeggiato è segnato come non attivo (per esempio perché in ferie), non riceve la mail personale ma può comunque apparire nella lista inviata ai colleghi, così sanno che dovranno fargli gli auguri al rientro;
- se in una certa sede e in un certo team non c’è nessun festeggiato, per quel gruppo non viene inviata alcuna email.

### Parametro di invio `exclude_birthday`

L’endpoint di invio supporta il parametro facoltativo `exclude_birthday`.

- Se `exclude_birthday=true` (valore di default), i festeggiati ricevono solo la mail personale e non ricevono anche la mail di team.
- Se `exclude_birthday=false`, i festeggiati vengono inclusi anche nella mail di team e quindi ricevono entrambe le email.

### Template email (EmailConfig)

Nel database esistono due template di base:

- il template con id 1 è usato per l’email di team, inviata ai colleghi non festeggiati;
- il template con id 2 è usato per l’email personale inviata al festeggiato.

Entrambi possono usare questi placeholder: `{date}`, `{employees}`, `{team}`, `{location}`.  
Il placeholder `{first_name}` è pensato per la mail personale (id 2).

Dal punto di vista delle API i template possono solo essere letti e modificati: non ci sono endpoint per crearli o cancellarli.

### Storico (BirthdayNotification)

Lo storico degli invii viene aggiornato solo quando, in una certa esecuzione, esiste almeno un festeggiato e viene spedita almeno una email.  
Se non parte nessuna email, non viene registrata alcuna riga nello storico.

---

## Endpoint principali

```
# Dipendenti
POST   /api/employees/createEmployee/ - Crea un dipendente
GET    /api/employees/getEmployees/?is_active=true - Get di tutti i dipendenti attivi
GET    /api/employees/getEmployee/<id>/ - Get di un dipendente dato l'id
PUT/PATCH  /api/employees/updateEmployee/<id>/ - Modifica un dipendente
DELETE     /api/employees/deleteEmployee/<id>/ - Eliminazione di un dipendente
GET        /api/employees/getTodayBirthdays/ - Dipendenti che compiono gli anni oggi

# Invio newsletter
POST   /api/notifications/sendToday/ - Invia mail ai team, visualizzabile da console
GET    /api/notifications/getNotifications/ - Restituisce in formato json il log delle mail inviate

# Template email (solo lettura e modifica, niente delete)
GET            /api/config/email/ - Get di tutti i template mail disponibili
GET            /api/config/email/getTemplate/<id>/ - Get di un template dato id
PUT/PATCH      /api/config/email/updateTemplate/<id>/ - Modifica un template dato id
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

Implementazioni future:

- Aggiunta e/o eliminazione di piu template
