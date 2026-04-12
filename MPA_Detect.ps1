# To start from commandline:
#
# powershell -ExecutionPolicy Bypass -File MPA_Detect.ps1
#   or
# powershell -ExecutionPolicy Bypass -File MPA_Detect.ps1 -Output
#
param (
    [switch]$Output # Dit maakt van --output een aan/uit schakelaar
)

# --- CONFIGURATIE ---
$ApiKey     = "Nr049axxJS8RaelrgoBgkl3B"
$WorkDir    = "C:/cam"
$InboxDir   = "C:/Users/Administrator/OneDrive/cam/ReoMPA"
$WebDir     = "C:/inetpub/wwwroot/ntfy"
$VenvPython = "C:/cam/venv/Scripts/python.exe"
$PyScript   = "C:/cam/MPA_Detect.py"
$LogFile    = "C:/cam/MPA_Detect_inspector.log"
$BaseUrl    = "http://212.132.96.72/ntfy"

$MaxLogSize = 10MB

# --- LOGGER FUNCTIE ---
function Write-PSLog($Message) {
    $Timestamp = Get-Date -Format "yyyy/MM/dd_HH:mm:ss"
    $Line = "$Timestamp $Message"
    #Add-Content -Path $LogFile -Value $Line
    [System.IO.File]::AppendAllText($LogFile, "$Line`r`n")
    Write-Host $Line
}

# --- NOTIFY FUNCTIE (Pushcut) ---
function Send-MPANotification($FullFileName) {
    # Check of de meldingen uitgeschakeld zijn
    $NotifOffFile = Join-Path $WorkDir "melding.off"
    if (Test-Path $NotifOffFile) {
        Write-PSLog "PUSH: Melding overgeslagen (melding.off gevonden)"
        return # Stop de functie hier
    }
    # Extract tijd uit filenaam: motion_20260316_114229.jpg
    # We gebruiken een simpele regex of split
    $TimePart = "Onbekend"
    if ($FullFileName -match "_(\d{2})(\d{2})(\d{2})\.") {
        $TimePart = "$($Matches[1]):$($Matches[2]):$($Matches[3])"
    }

    $ImageUri = "$BaseUrl/$FullFileName"

    $Body = @{
        title = "MPA Car Detected @ $TimePart"
        text  = "Start a session?"
        image = $ImageUri
    } | ConvertTo-Json

    $Headers = @{
        "API-Key"      = $ApiKey
        "Content-Type" = "application/json"
    }

    try {
        Invoke-RestMethod -Method Post -Uri "https://api.pushcut.io/v1/notifications/MPA_Alert" -Headers $Headers -Body $Body
        Write-PSLog "PUSH: Melding verzonden voor $FullFileName (Tijd: $TimePart)"
    } catch {
        Write-PSLog "ERROR: Pushcut mislukt: $_"
    }
}

function Run-Cleanup {
    Write-PSLog "CLEANUP: Start grote kuis in $WebDir..."
    $Limit = (Get-Date).AddHours(-1)

    # We pakken alle bestanden in de webmap
    #$OldFiles = Get-ChildItem -Path $WebDir -File | Where-Object { $_.LastWriteTime -lt $Limit }
    $OldFiles = Get-ChildItem -Path (Join-Path $WebDir "*") -File -Exclude "web.config" | Where-Object { $_.LastWriteTime -lt $Limit }

    if ($OldFiles) {
        foreach ($File in $OldFiles) {
            try {
                Remove-Item $File.FullName -Force -ErrorAction Stop
                Write-PSLog "CLEANUP: Verwijderd: $($File.Name) (Datum: $($File.LastWriteTime))"
            } catch {
                Write-PSLog "ERROR: Kon $($File.Name) niet verwijderen: $_"
            }
        }
    } else {
        Write-PSLog "CLEANUP: Geen oude bestanden gevonden."
    }
}

# --- HOOFDPROGRAMMA ---
Write-PSLog "PowerShell Inspecteur gestart."

# Zet dit op een tijdstip in het verleden, zodat hij bij de EERSTE loop meteen de cleanup doet.
$LastCleanup = (Get-Date).AddHours(-2)

# --- INBOX OPSCHONEN BIJ OPSTART ---
Write-PSLog "STARTUP: InboxDir leegmaken..."
#$OldVideos = Get-ChildItem -Path $InboxDir -Include "*.mp4", "*.mp4.processing", "*.mp4.done" -File
$OldVideos = Get-ChildItem -Path (Join-Path $InboxDir "*") -Include "*.mp4", "*.processing", "*.done" -File
if ($OldVideos) {
    foreach ($File in $OldVideos) {
        try {
            Remove-Item $File.FullName -Force -ErrorAction Stop
            Write-PSLog "STARTUP: Oude video verwijderd: $($File.Name)"
        } catch {
            Write-PSLog "ERROR: Kon $($File.Name) niet verwijderen bij opstart: $_"
        }
    }
} else {
    Write-PSLog "STARTUP: Inbox was al leeg."
}


while ($true) {
    $Nu = Get-Date -Format "HHmm"
    if ([int]$Nu -ge 2355 -or [int]$Nu -lt 0900) {
        Write-PSLog "TIJDSSLOT: Buiten werkuren ($Nu). Script stopt nu zelfstandig."
        break # Verlaat de lus en sluit het script netjes af
    }

    # Check cleanup.
    if ((Get-Date) -gt $LastCleanup.AddMinutes(3)) {
        Run-Cleanup
        $LastCleanup = Get-Date # Reset de timer naar NU
    }

    # Pak MP4's, sorteer op creatiedatum (oudste eerst)
    $Videos = Get-ChildItem -Path $InboxDir -Filter "*.mp4" | Sort-Object CreationTime

    foreach ($Video in $Videos) {
        $OriginalName = $Video.Name
        $CurrentPath  = $Video.FullName

        # Stap 1: Hernoem direct naar .processing om dubbele verwerking te voorkomen
        $ProcessingPath = $CurrentPath + ".processing"
        try {
            Rename-Item -Path $CurrentPath -NewName ($OriginalName + ".processing") -ErrorAction Stop
        } catch {
            continue # Bestand is waarschijnlijk nog in gebruik door OneDrive
        }

        Write-PSLog "EXEC: Start verwerking $OriginalName"

        # Check of de 'opname-schakelaar' aan staat
        $TriggerFile = Join-Path $WorkDir "record.on"
        $RecordingEnabled = Test-Path $TriggerFile

        if ($RecordingEnabled) {
            Write-PSLog "INFO: Opname-modus ACTIEF (record.on gevonden)"
            $PythonArgs = "--output"
        } else {
            $PythonArgs = "" # Geen output argument doorgeven
        }

        # Check of de 'melding-schakelaar' aan staat
        $NotifOffFile = Join-Path $WorkDir "melding.off"
        if (Test-Path $NotifOffFile) {
            $Global:NotifStatus = "GEDEMPT"
        } else {
            # Als hij net weer is aangezet, loggen we dat één keer
            if ($Global:NotifStatus -eq "GEDEMPT") {
                Write-PSLog "INFO: Meldingen zijn zojuist HERVAT (melding.off verwijderd)."
                $Global:NotifStatus = "ACTIEF"
            }
        }

        # args override recording switch.
        if ($Output) {
            $PythonArgs = "--output"
        }

        # Start Python met de dynamische argumenten
        #$Proc = Start-Process python.exe -ArgumentList $PyScript, "`"$VideoPath`"", $PythonArgs -Wait -NoNewWindow -PassThru
        & $VenvPython $PyScript $ProcessingPath $PythonArgs
        ########


        # Stap 2: Start Python script.
        #if ($Output) {
        #    & $VenvPython $PyScript $ProcessingPath --output
        #}
        #else {
        #    & $VenvPython $PyScript $ProcessingPath
        #}
        $Result = $LASTEXITCODE

        # Zoek de gegenereerde video.
        # We hernoemen deze naar iets mooiers op de webmap.
        # Zoek naar elk bestand dat eindigt op _detected.mp4 in de werkmap.
        # We gebruiken de naam van de video als basis om het juiste bestand te pakken.
        $SearchPattern = "*$($OriginalName.Replace('.mp4',''))*_detected.mp4"
        $VidSourceFile = Get-ChildItem -Path $InboxDir -Filter $SearchPattern | Select-Object -First 1

        if ($VidSourceFile) {
            $VidSource = $VidSourceFile.FullName
            $FinalVidName = $OriginalName.Replace(".mp4", "_detected.mp4")
            $WebVidDest = Join-Path $WebDir $FinalVidName

            # Kopieer en fix rechten
            Copy-Item -Path $VidSource -Destination $WebVidDest -Force
            $Acl = Get-Acl $WebVidDest
            $Acl.SetAccessRuleProtection($false, $false)
            Set-Acl $WebVidDest $Acl

            Write-PSLog "MOVE: Video-output naar webmap: $FinalVidName"
            Remove-Item $VidSource -Force
        }

        if ($Result -eq 10) {
            # MPA gevonden. De JPG staat naast de .processing file
            $JpgSource = [System.IO.Path]::ChangeExtension($ProcessingPath, ".jpg")
            $FinalJpgName = [System.IO.Path]::ChangeExtension($OriginalName, ".jpg")
            $WebDest = Join-Path $WebDir $FinalJpgName

            if (Test-Path $JpgSource) {
                # 1. Gebruik Copy-Item in plaats van Move-Item (veiliger voor rechten)
                Copy-Item -Path $JpgSource -Destination $WebDest -Force

                # 2. Forceer dat het nieuwe bestand de rechten van de ntfy-map overneemt
                $Acl = Get-Acl $WebDest
                $Acl.SetAccessRuleProtection($false, $false) # Schakel overerving IN
                Set-Acl $WebDest $Acl

                Write-PSLog "MOVE: Snapshot gekopieerd naar $WebDir en rechten hersteld."

                # 3. Verstuur de notificatie
                Send-MPANotification -FullFileName $FinalJpgName

                # 4. Verwijder nu het origineel in de werkmap
                Remove-Item $JpgSource -Force
            }
        }


        # Stap 3: Vertraging berekenen
        # We halen de pure bestandsnaam uit het volledige pad (bijv. C:\temp\motion_...mp4 -> motion_...mp4)
        $huidigBestand = Split-Path $ProcessingPath -Leaf

        if ($huidigBestand -match '(\d{8})_(\d{6})') {
            $fileTimeStr = $matches[1] + " " + $matches[2]
            $fileDateTime = [datetime]::ParseExact($fileTimeStr, "yyyyMMdd HHmmss", $null)
            $diff = [math]::Round(((Get-Date) - $fileDateTime).TotalMinutes)
        } else {
            $diff = 0
        }

        # Update de status.json
        $statusObj = @{
            last_run = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
            delay = $diff
        } | ConvertTo-Json

        $statusObj | Out-File -FilePath "C:\inetpub\wwwroot\ntfy\status.json" -Encoding utf8 -Force



        # Stap 4: Markeer als klaar (Hernoemen i.p.v. Verwijderen)
        $DonePath = $CurrentPath + ".done"

        try {
            # We halen de .processing eraf en zetten er .done achter
            Rename-Item -Path $ProcessingPath -NewName ($OriginalName + ".done") -Force
            Write-PSLog "DONE: $OriginalName verwerkt en hernoemd naar .done"
        } catch {
            Write-PSLog "ERROR: Kon $OriginalName niet hernoemen naar .done: $_"
        }

    }

    # Als er geen mp4 bestanden meer klaarstaan, zet delay op 0
    $restant = Get-ChildItem "$InboxDir\*.mp4" | Measure-Object
    if ($restant.Count -eq 0) {
        $statusObj = @{ last_run = (Get-Date -Format "yyyy-MM-dd HH:mm:ss"); delay = 0 } | ConvertTo-Json
        $statusObj | Out-File -FilePath "C:\inetpub\wwwroot\ntfy\status.json" -Encoding utf8 -Force
    }

    # --- CHECK VOOR HERSTART COMMANDO ---
    $RestartTrigger = Join-Path $WorkDir "restart.trigger"
    if (Test-Path $RestartTrigger) {
        Remove-Item $RestartTrigger -Force
        Write-PSLog "SYSTEM: Herstart commando ontvangen via Dashboard. Script sluit af..."
        Set-Content -Path "C:\cam\start.trigger" -Value "start aanvragen"
        exit 1 # Dit stopt het script
    }





    Start-Sleep -Seconds 1

    if (Test-Path $LogFile) {
        $FileSize = (Get-Item $LogFile).Length
        if ($FileSize -gt $MaxLogSize) {
            Remove-Item $LogFile -Force
            # Optioneel: Maak direct een nieuwe lege file aan met een start-melding
            "--- Log gereset op $(Get-Date) wegens grootte ($($FileSize / 1MB) MB) ---" | Out-File $LogFile
        }
    }

}
