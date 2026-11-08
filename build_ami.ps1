# Compile la version « ami » (ClavierFR) : signée avec ta propre clé (voir README : keytool), sans outils de dev.
# La clé et son mot de passe sont HORS du projet : %USERPROFILE%\ClavierFR-cles ou $env:CLAVIERFR_CLES (à sauvegarder, sinon impossible de faire des mises à jour).
$ErrorActionPreference = "Stop"
$racine = $PSScriptRoot
$cles = if ($env:CLAVIERFR_CLES) { $env:CLAVIERFR_CLES } else { "$env:USERPROFILE\ClavierFR-cles" }
$infos = Get-Content "$cles\cle.txt" | ForEach-Object { $k,$v = $_ -split "=",2; @{ $k = $v } }
$alias = ($infos | Where-Object { $_.alias }).alias; $mdp = ($infos | Where-Object { $_.motdepasse }).motdepasse
$env:CLAVIERFR_KS_FILE = "$cles\clavierfr.jks"; $env:CLAVIERFR_KS_ALIAS = $alias; $env:CLAVIERFR_KS_PASS = $mdp
if (-not $env:JAVA_HOME) { $env:JAVA_HOME = "C:\Users\Doanh\Documents\Codex\AndroidDev\java\jdk-17.0.20.1+1" }  # JDK 17 : definir JAVA_HOME ailleurs
$env:Path = "$env:JAVA_HOME\bin;$env:Path"
$env:PYTHONUTF8 = "1"
Set-Location "$racine\futo-keyboard"
& .\gradlew.bat assembleAmiRelease -PnoMinify
if ($LASTEXITCODE -ne 0) { throw "Build en echec" }
New-Item -ItemType Directory -Force "$racine\apk\ami" | Out-Null
Copy-Item "build\outputs\apk\ami\release\futo-keyboard-ami-release.apk" "$racine\apk\ami\ClavierFR.apk" -Force
Copy-Item "$racine\futo-keyboard\LICENSE.md" "$racine\apk\ami\LICENCE-FUTO.md" -Force
Write-Host "APK ami : $racine\apk\ami\ClavierFR.apk"
