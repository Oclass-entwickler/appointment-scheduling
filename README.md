

## 1. Vorbereitungen

1. **Repository klonen** oder Projektordner herunterladen.  
2. **Python-Umgebung** einrichten (optional, aber empfohlen):  
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```
3. **Abhängigkeiten installieren**:  
   ```bash
   pip install -r requirements.txt
   ```
4. **Datenbank** wird beim ersten Start automatisch angelegt (sofern in der `app.py` / `models.py` entsprechend konfiguriert).  

## 2. Starten der Anwendung

```bash
python app.py
```

Die Anwendung läuft nun standardmäßig unter:
```
http://127.0.0.1:5000
```

## 3. Funktionale Übersicht

1. **Termin buchen**  
   - Nutzer geht auf „Termin buchen“ (Menüpunkt), wählt die Terminart (z. B. „Pass Antrag“).  
   - Anschließend wählt er aus den **verfügbaren Terminen** ein Datum und eine Uhrzeit.  
   - Name, E-Mail, Geburtsdatum (optional) werden eingegeben, Termin wird gebucht.  
   - Eine **Bestätigungs-E-Mail** (wenn konfiguriert) wird gesendet.  
2. **Status prüfen**  
   - Nutzer gibt seine **Termin-Nummer** (und je nach Konfiguration auch Name / Geburtsdatum) ein.  
   - Sieht den aktuellen Status (z. B. „Angemeldet“).  
3. **Admin-Bereich**  
   - Zeigt „Alle Termine“ (aktueller und noch nicht abgelaufener Zeitraum) an.  
   - Admin kann **Termine suchen** (nach Name), **ablehnen**, **löschen** und Terminarten / Zeitfenster verwalten.  
   - **Automatisches oder manuelles Löschen**:  
     - **Automatisch**: Beim Aufruf der Admin-Seite werden alle Termine gelöscht, deren Datum älter als 2 Tage ist.  
     - **Manuell**: Ein Button „Alte Termine aufräumen“ löscht alle Termine, deren Datum älter als 2 Tage ist.  
       (Je nach Variante, die Sie in `app.py` umgesetzt haben.)

## 4. Konfiguration & E-Mail-Versand (optional)

- Wenn Sie **Flask-Mail** nutzen, passen Sie in Ihrer `config.py` die Mail-Parameter an (z. B. Gmail-Server).  
- Legen Sie ggf. **Umgebungsvariablen** (`MAIL_USERNAME`, `MAIL_PASSWORD`) fest.  

Beispiel `.env`:
```
MAIL_USERNAME=hasankeisar@gmail.com oder  
MAIL_PASSWORD=mein_app_passwort
MAIL_DEFAULT_SENDER=hasankeisar@gmail.com

or

$env:MAIL_USERNAME = "hasankeisar@gmail.com"
$env:MAIL_PASSWORD = "oate yljt eetx uokp"
$env:MAIL_DEFAULT_SENDER = "hasankeisar@gmail.com"

```

Anschließend werden nach erfolgreicher Terminbuchung Bestätigungs-E-Mails versendet.

---

## 5. Zusammenfassung

- **Start**: `python app.py` (oder über WSGI-Server wie Gunicorn/uwsgi)  
- **Nutzung**:  
  - **`/`** – Startseite  
  - **`/book`** – Termin buchen  
  - **`/status`** – Terminstatus prüfen  
  - **`/admin`** – Admin-Bereich (Termine, Zeitfenster, Terminarten etc.)  
- **Bereinigung alter Termine**:  
  - Entweder automatisch beim Seitenaufruf oder manuell via Button (je nach Konfiguration).  
