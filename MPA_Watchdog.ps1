while($true) {
    Write-Host "Inspecteur wordt gestart..."
    powershell.exe -ExecutionPolicy Bypass -File "C:\cam\MPA_Detect.ps1"
    Write-Host "Inspecteur is gestopt. Herstarten over 5 seconden..."
    Start-Sleep -Seconds 5
}
