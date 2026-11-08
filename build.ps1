# Compile l'APK (debug) et le copie dans <racine>\apk\
$ErrorActionPreference = "Stop"
$racine = $PSScriptRoot
if (-not $env:JAVA_HOME) { $env:JAVA_HOME = "C:\Users\Doanh\Documents\Codex\AndroidDev\java\jdk-17.0.20.1+1" }  # JDK 17 : definir JAVA_HOME ailleurs
$env:Path = "$env:JAVA_HOME\bin;$env:Path"
$env:PYTHONUTF8 = "1"   # le script updateLocales lit de l'UTF-8
Set-Location "$racine\futo-keyboard"
& .\gradlew.bat assembleUnstableDebug
if ($LASTEXITCODE -ne 0) { throw "Build en echec" }
New-Item -ItemType Directory -Force "$racine\apk" | Out-Null
Copy-Item "build\outputs\apk\unstable\debug\futo-keyboard-unstable-debug.apk" "$racine\apk\ClavierFR-debug.apk" -Force
Write-Host "APK : $racine\apk\ClavierFR-debug.apk"
