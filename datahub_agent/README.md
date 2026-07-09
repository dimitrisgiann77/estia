# Data Hub Agent (on-prem)

Τραβάει **ΟΛΑ τα πεδία** της Business Μισθοδοσίας Epsilon (read-only) και τα σπρώχνει στην Εστία.

## Εγκατάσταση στον CND_SERVER
1. Αντίγραψε τον φάκελο `datahub_agent/` στον CND_SERVER (π.χ. `C:\estia_agent\`).
2. `pip install pyodbc requests certifi` (Python 3.8+). Χρειάζεται **ODBC Driver 17 for SQL Server**.
3. Φτιάξε **read-only login** στη `bmisthos`: ρόλος `db_datareader` (ΚΑΜΙΑ εγγραφή/DDL).
4. Αντίγραψε `.env.example` → `.env` και συμπλήρωσε (connection string + Estia token).
5. Δοκιμή: `python agent.py --dry` (δείχνει τι θα σταλεί, χωρίς αποστολή).

## Χρήση
- `python agent.py --seed`  → εφάπαξ πλήρες (όλα τα έτη + όλο το μητρώο).
- `python agent.py --live`  → incremental (νέες/αλλαγμένες γραμμές + snapshot ταυτοτήτων).
- `python agent.py --tier A`→ μόνο ταυτότητες (γρήγορο).

## Χρονοπρογραμματισμός (Windows Task Scheduler)
- Tier A + Tier B incremental: `agent.py --live` κάθε βράδυ (π.χ. 02:00).
- Tier A snapshot συχνά (π.χ. ωριαία): `agent.py --tier A`.

## Ασφάλεια
- Login **μόνο db_datareader**. Outbound HTTPS μόνο (TLS via certifi). Token & connection string **στο `.env`**, όχι στον κώδικα. Binary (φωτο/CV/attachments) **δεν** αποστέλλονται.
