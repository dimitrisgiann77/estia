@echo off
REM ── Data Hub Agent — setup (τρέξε το ΜΙΑ φορά στον CND_SERVER) ──
chcp 65001 >nul
echo === Data Hub Agent setup ===
echo.
echo [1/3] Ελεγχος Python...
python --version || (echo ΣΦΑΛΜΑ: δεν βρεθηκε Python. Εγκατεστησε Python 3.8+ & pause & exit /b 1)
echo.
echo [2/3] Εγκατασταση βιβλιοθηκων (pyodbc, requests, certifi)...
python -m pip install --upgrade pyodbc requests certifi || (echo ΣΦΑΛΜΑ στο pip install & pause & exit /b 1)
echo.
echo [3/3] Ρυθμιση .env...
if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo Δημιουργηθηκε .env — ΑΝΟΙΞΕ ΤΟ και συμπληρωσε connection string + token.
) else (
  echo Υπαρχει ηδη .env — ok.
)
echo.
echo === Ετοιμο ===
echo Επομενο: (1) συμπληρωσε το .env  (2) τρεξε:  python agent.py --dry
pause
