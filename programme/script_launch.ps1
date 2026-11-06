$Executable = "watchdog_convention.py" 
$FichierDossiers = "dossiers.txt"

if (-not (Test-Path $FichierDossiers)) {
    Write-Error "Le fichier '$FichierDossiers' est introuvable à côté du script."
    Read-Host "Appuyez sur Entrée pour quitter..."
    Exit
}

$Dossiers = Get-Content $FichierDossiers | Where-Object { $_.Trim() -ne "" }

Write-Host "--- DÉMARRAGE DE LA SURVEILLANCE ---" -ForegroundColor Cyan
Write-Host "Nombre de dossiers détectés : $($Dossiers.Count)"

foreach ($Dossier in $Dossiers) {
    $Dossier = $Dossier.Trim()

    if (Test-Path $Dossier) {
        Start-Process python -ArgumentList "`"$Executable`"", "`"$Dossier`"" -WindowStyle Normal
    } else {
        Write-Warning "[ATTENTION] Le dossier suivant n'existe pas et sera ignoré : $Dossier"
    }
}

Write-Host "`nTous les processus ont été lancés dans des fenêtres séparées." -ForegroundColor Cyan

