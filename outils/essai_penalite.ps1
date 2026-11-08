param([double]$pen, [string]$tag)
$r="C:\Users\Doanh\Desktop\Programme IA\clavierPers"; $adb="C:\Users\Doanh\AppData\Local\Android\Sdk\platform-tools\adb.exe"
cd "$r\ml"; $env:Path="$PWD\venv\Lib\site-packages\executorch\data\bin;$env:Path"; $env:PYTHONUTF8="1"
$null = .\venv\Scripts\python.exe export.py --run runs\fw1h --data data\fw --out export\pen$tag --codename hungry_jellyfish --hash_penalty $pen 2>$null
Copy-Item "export\pen$tag\context_lm.pte" "$r\futo-keyboard\java\assets\futo-swipe\french_lm\" -Force
& "$r\build.ps1" *> "$r\build_pen.log"
& $adb install -r "$r\apk\ClavierFR-debug.apk" | Out-Null
$f="/sdcard/Android/data/org.futo.inputmethod.latin.unstable/files/replay_last.json"
for ($try=0; $try -lt 3; $try++) {
  & $adb shell rm -f $f
  & $adb shell am start -f 0x18000000 -n org.futo.inputmethod.latin.unstable/org.futo.inputmethod.latin.SwipeRecorderActivity --ez replay true --ei beam 300 | Out-Null
  $ok = $false
  for ($i=0; $i -lt 24; $i++) { $x = & $adb shell "test -f $f && echo yes"; if ($x -match "yes") { $ok = $true; break }; Start-Sleep 5 }
  if ($ok) { break }
}
Start-Sleep 3
& $adb pull /sdcard/Android/data/org.futo.inputmethod.latin.unstable/files/replay_last.json "$r\donnees\replay_pen$tag.json" | Out-Null
$j = Get-Content "$r\donnees\replay_pen$tag.json" -TotalCount 1 | ConvertFrom-Json
"pénalité $pen : top-1 $([math]::Round($j.top1,1)) % · top-4 $([math]::Round($j.top4,1)) %"
