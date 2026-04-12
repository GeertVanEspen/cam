@echo off
set "triggerFile=C:\cam\start.trigger"
set "taskName=MPA_Detect_Daily"

:loop
if exist "%triggerFile%" (
    echo [%date% %time%] Trigger gevonden. Taak starten...
    
    :: De taak starten
    schtasks /run /tn "%taskName%"
    
    :: Het triggerbestand verwijderen
    del "%triggerFile%"
    
    echo [%date% %time%] Taak gestart en trigger verwijderd.
)

:: Korte pauze (bijv. 15 seconden) om CPU-belasting te minimaliseren
timeout /t 15 /nobreak >nul
goto loop

