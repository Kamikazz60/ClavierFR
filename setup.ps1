# Prépare le dossier futo-keyboard\ : FUTO Keyboard (version de référence) + sous-modules + fichiers ClavierFR.
# Prérequis : git, git-lfs (les modèles FUTO Swipe sont sur Hugging Face), SDK Android (ANDROID_HOME ou ANDROID_SDK_ROOT).
$ErrorActionPreference = "Stop"
$racine = $PSScriptRoot
$cible = "$racine\futo-keyboard"
$commit = "7d61ab413"          # voir base.txt
if (Test-Path $cible) { throw "$cible existe déjà : supprime-le ou renomme-le avant de relancer." }

git clone https://github.com/futo-org/android-keyboard $cible
Set-Location $cible
git checkout $commit
git submodule update --init --recursive

# fichiers modifiés / ajoutés par ClavierFR (mêmes chemins que dans futo-keyboard\)
Copy-Item "$racine\overlay\*" $cible -Recurse -Force
# modèle de langue français (ContextLM) à côté des modèles FUTO Swipe
New-Item -ItemType Directory -Force "$cible\java\assets\futo-swipe\french_lm" | Out-Null
Copy-Item "$racine\modele-fr\*" "$cible\java\assets\futo-swipe\french_lm" -Force

$sdk = if ($env:ANDROID_HOME) { $env:ANDROID_HOME } elseif ($env:ANDROID_SDK_ROOT) { $env:ANDROID_SDK_ROOT } else { throw "Définis ANDROID_HOME (dossier du SDK Android)." }
"sdk.dir=" + ($sdk -replace '\','\') | Set-Content "$cible\local.properties" -Encoding ascii
Write-Host "Prêt. Pour compiler : .\build_ami.ps1 (version à distribuer) ou .\build.ps1 (version de développement)."
