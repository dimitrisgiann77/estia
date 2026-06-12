# Sergios Hotel — Water Log

Web εφαρμογή καταγραφής μετρήσεων νερού χρήσης (CLO₂, θερμοκρασία, pH) για το Sergios Hotel.
Το προσωπικό καταγράφει μετρήσεις πρωί/απόγευμα, αποθηκεύονται σε βάση δεδομένων και
αποστέλλεται αυτόματα email αναφορά με έλεγχο ορίων (OK / ΠΡΟΣΟΧΗ).

## Τεχνολογίες

- **Backend:** Flask + Flask-SQLAlchemy
- **Βάση:** PostgreSQL (production) / SQLite (τοπικά)
- **Email:** SMTP (SSL)
- **Deploy:** Railway (gunicorn)
- **Γλώσσες:** Ελληνικά / Αγγλικά

## Δομή

```
app.py             # Backend: routes, μοντέλα, αποστολή email
requirements.txt   # Python εξαρτήσεις
railway.json       # Ρυθμίσεις deploy στο Railway
static/            # app.js, style.css
templates/         # login, app, dashboard, edit (HTML)
```

## Τοπική εκτέλεση

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # συμπλήρωσε τις τιμές
python app.py
```

Άνοιξε http://localhost:5000

## Μεταβλητές περιβάλλοντος

Δες το `.env.example`. Βασικές: `SECRET_KEY`, `DATABASE_URL`, `EMAIL_FROM`, `EMAIL_PASSWORD`.

## Προεπιλεγμένοι χρήστες (πρώτη εκκίνηση)

Δημιουργούνται αυτόματα στην πρώτη εκτέλεση (`init_db`). **Άλλαξε τους κωδικούς μετά την πρώτη είσοδο.**

| Username  | Ρόλος  |
|-----------|--------|
| admin     | admin  |
| giannhs   | admin  |
| xypakis   | staff  |

## Όρια μετρήσεων

- **CLO₂:** 1.0–2.0 ppm
- **Θερμοκρασία δεξαμενής:** ≤ 20 °C
- **ΖΝΧ αναχώρηση:** ≥ 60 °C, **επιστροφή:** ≥ 50 °C
- **Ζεστό νερό σημείων:** ≥ 50 °C

## Σημειώσεις ασφάλειας

Πριν από παραγωγική χρήση συνιστάται: μεταφορά όλων των κωδικών/κλειδιών σε μεταβλητές
περιβάλλοντος, προσθήκη προστασίας CSRF, και μετατροπή των ενεργειών διαγραφής σε POST.
