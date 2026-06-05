# 🏊 Sergios Hotel — Pool Management App

## Τι περιλαμβάνει η εφαρμογή

- **Login** για υπευθύνους και admin
- **Μετρήσεις** με αυτόματο υπολογισμό χημικών
- **Checklist** ημερήσιων εργασιών + φωτογραφία πισίνας
- **Οδηγίες** 10 διαδικασιών (Ελληνικά / Αγγλικά)
- **Email report** αυτόματα σε κάθε υποβολή
- **Dashboard** με ιστορικό και γραφήματα για admin
- **PWA** — εγκαθίσταται σαν app στο κινητό

---

## Βήμα 1: Δημιουργία λογαριασμού Railway

1. Πήγαινε στο https://railway.app
2. Κάνε "Sign Up" με Google ή GitHub
3. Επίβεβαίωσε το email σου

---

## Βήμα 2: Δημιουργία λογαριασμού SendGrid (για emails)

1. Πήγαινε στο https://sendgrid.com
2. Κάνε "Start For Free" (100 emails/ημέρα δωρεάν)
3. Επιβεβαίωσε το email σου
4. Πήγαινε: Settings → API Keys → Create API Key
5. Επίλεξε "Full Access" → Create
6. **Αντέγραψε και φύλαξε** το API key (εμφανίζεται μόνο μια φορά!)
7. Πήγαινε: Settings → Sender Authentication → Single Sender Verification
8. Πρόσθεσε το email σου (π.χ. info@sergioshotel.gr) και επιβεβαίωσε

---

## Βήμα 3: Upload κώδικα στο GitHub

1. Πήγαινε στο https://github.com και κάνε λογαριασμό (αν δεν έχεις)
2. Κάνε κλικ "+" → "New repository"
3. Όνομα: `sergios-pool`
4. Private ✓ → Create repository
5. Κατέβασε τον φάκελο `sergios-pool` στον υπολογιστή σου
6. Ακολούθησε τις οδηγίες του GitHub για "upload files"
7. Ανέβασε όλα τα αρχεία

---

## Βήμα 4: Deploy στο Railway

1. Πήγαινε στο https://railway.app → "New Project"
2. Επίλεξε "Deploy from GitHub repo"
3. Σύνδεσε τον GitHub λογαριασμό σου
4. Επίλεξε το `sergios-pool` repository
5. Railway θα αρχίσει αυτόματα το build

---

## Βήμα 5: Ρύθμιση Environment Variables

Στο Railway, πήγαινε στο project → Settings → Variables
Πρόσθεσε τις παρακάτω μεταβλητές:

```
SECRET_KEY          = κάποιος-τυχαίος-κωδικός-π.χ.-sergios2024abc
SENDGRID_API_KEY    = το API key που πήρες από SendGrid
EMAIL_FROM          = info@sergioshotel.gr  (το επιβεβαιωμένο email)
EMAIL_TO            = info@sergioshotel.gr  (που θα λαμβάνεις reports)
```

---

## Βήμα 6: Αρχικοποίηση βάσης δεδομένων

Στο Railway → project → Shell (ή Deployments → latest → View Logs):

```bash
python -c "from app import init_db; init_db()"
```

---

## Βήμα 7: Πάρε τον σύνδεσμο

Στο Railway → Settings → Domains → Generate Domain
Θα πάρεις κάτι σαν: `sergios-pool.up.railway.app`

---

## Αρχικοί λογαριασμοί

| Username | Password    | Ρόλος |
|----------|-------------|-------|
| admin    | sergios2024 | Admin |
| giannhs  | pool2024    | Admin |

⚠️ **ΑΛΛΑΞΕ ΤΟΥΣ ΚΩΔΙΚΟΥΣ** αμέσως μετά την πρώτη είσοδο!

---

## Εγκατάσταση σαν App στο κινητό

### iPhone (iOS):
1. Άνοιξε Safari
2. Πήγαινε στη διεύθυνση της εφαρμογής
3. Κάνε login
4. Πάτα το κουμπί "Κοινοποίηση" (□↑)
5. Επίλεξε "Προσθήκη στην Αρχική Οθόνη"

### Android:
1. Άνοιξε Chrome
2. Πήγαινε στη διεύθυνση της εφαρμογής
3. Κάνε login
4. Πάτα τις 3 τελείες (⋮) πάνω δεξιά
5. Επίλεξε "Προσθήκη στην αρχική οθόνη"

---

## Προσθήκη νέου υπευθύνου πισίνας

1. Κάνε login ως admin
2. Πήγαινε στο Dashboard
3. Κάτω δεξιά: "Νέος χρήστης"
4. Συμπλήρωσε: Ονοματεπώνυμο, Username, Password
5. Role: Staff (υπεύθυνος)
6. Γλώσσα: Ελληνικά ή English

---

## Μελλοντικές αλλαγές

Για οποιαδήποτε αλλαγή (νέα πεδία, αλλαγή δοσολογιών, κτλ):
1. Ανέβασε τα αλλαγμένα αρχεία στο GitHub
2. Το Railway κάνει αυτόματα deploy σε 2-3 λεπτά

---

## Υποστήριξη

Για τεχνική βοήθεια, επικοινώνησε με Claude (claude.ai)
και παρέχε τον κώδικα για να βοηθήσει με αλλαγές.

---

*Sergios Hotel — Pool Management System v1.0*
*Χερσόνησος Κρήτης*
