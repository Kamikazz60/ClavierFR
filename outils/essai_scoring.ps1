param([string]$alpha="-",[string]$beta="-",[string]$gamma="-",[string]$lambda="-",[string]$tag="x")
$r="C:\Users\Doanh\Desktop\Programme IA\clavierPers"; $adb="C:\Users\Doanh\AppData\Local\Android\Sdk\platform-tools\adb.exe"
$f="/sdcard/Android/data/org.futo.inputmethod.latin.unstable/files/replay_last.json"
$null = python "$r\patch_aar.py" $alpha $beta $gamma $lambda
& "$r\build.ps1" *> "$r\build_sc.log"
& $adb install -r "$r\apk\ClavierFR-debug.apk" | Out-Null
for ($try=0; $try -lt 3; $try++) {
  & $adb shell rm -f $f
  & $adb shell am start -f 0x18000000 -n org.futo.inputmethod.latin.unstable/org.futo.inputmethod.latin.SwipeRecorderActivity --ez replay true --ei beam 300 | Out-Null
  $ok=$false; for ($i=0;$i -lt 24;$i++){ if ((& $adb shell "test -f $f && echo yes") -match "yes"){$ok=$true;break}; Start-Sleep 5 }
  if ($ok) { break }
}
Start-Sleep 3
& $adb pull $f "$r\donnees\replay_sc_$tag.json" | Out-Null
"a=$alpha b=$beta g=$gamma l=$lambda : " + (python "$r\essai_scoring.py" score "$r\donnees\replay_sc_$tag.json")
