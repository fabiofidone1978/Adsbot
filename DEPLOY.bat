@echo off
REM ========================================
REM ADSBOT - Production Deployment Script
REM ========================================
REM Version: 2.0
REM Date: 2024-12-03

setlocal enabledelayedexpansion
cd /d "d:\Documents and Settings\fabio-fidone\My Documents\Adsbot"

echo.
echo ========================================
echo ADSBOT - Production Deployment Script
echo ========================================
echo.

REM Step 1: Verifica Python
echo [1/5] Verifying Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python non trovato!
    echo Installa Python 3.10+ da: https://www.python.org/
    pause
    exit /b 1
)
echo OK: Python trovato

REM Step 2: Verifica dipendenze
echo.
echo [2/5] Checking dependencies...
python -c "import telegram; import sqlalchemy; import stripe" >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: Dipendenze mancanti
    echo Installo dipendenze...
    pip install -q -r requirements.txt
    if %errorlevel% neq 0 (
        echo ERROR: Installazione dipendenze fallita!
        pause
        exit /b 1
    )
    echo OK: Dipendenze installate
) else (
    echo OK: Tutte le dipendenze presenti
)

REM Step 3: Verifica compilazione
echo.
echo [3/5] Verifying code compilation...
python -m py_compile adsbot/bot.py adsbot/campaigns.py adsbot/analytics.py >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Compilazione fallita!
    echo Esegui: python -m py_compile adsbot/bot.py
    pause
    exit /b 1
)
echo OK: Codice compilato correttamente

REM Step 4: Backup database
echo.
echo [4/5] Creating database backup...
if exist adsbot.db (
    copy adsbot.db adsbot.db.backup >nul 2>&1
    echo OK: Backup creato: adsbot.db.backup
) else (
    echo OK: Nessun database precedente
)

REM Step 5: Esegui tests
echo.
echo [5/5] Running integration tests...
python test_integration.py >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Integration tests falliti!
    echo Esegui: python test_integration.py
    pause
    exit /b 1
)
echo OK: Tutti i test passati

REM All checks passed
echo.
echo ========================================
echo.✅ DEPLOYMENT VERIFICATION COMPLETE
echo.
echo Status: READY FOR PRODUCTION
echo.
echo Next steps:
echo   1. Verifica config.ini sia configurato
echo   2. Avvia bot: python main.py
echo   3. Test in Telegram: /start
echo   4. Monitora logs per errori
echo.
echo ========================================
echo.

REM Opzioni
echo Cosa vuoi fare ora?
echo.
echo [1] Avvia bot (python main.py)
echo [2] Esegui tests di nuovo
echo [3] Edita config.ini
echo [4] Esci
echo.
set /p choice="Seleziona opzione (1-4): "

if "%choice%"=="1" (
    cls
    echo Starting Adsbot...
    echo.
    python main.py
) else if "%choice%"=="2" (
    cls
    python test_integration.py
    pause
) else if "%choice%"=="3" (
    start notepad config.ini
) else (
    echo Arrivederci!
    exit /b 0
)

endlocal
pause
