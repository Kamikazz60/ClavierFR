param([string]$tag="x",[int]$tries=-1,[int]$beam=300,[int]$pf=0)
$r="C:\Users\Doanh\Desktop\Programme IA\clavierPers"; $adb="C:\Users\Doanh\AppData\Local\Android\Sdk\platform-tools\adb.exe"
$f="/sdcard/Android/data/org.futo.inputmethod.latin.unstable/files/replay_last.json"
for ($try=0; $try -lt 3; $try++) {
  & $adb shell rm -f $f; & $adb logcat -c
  & $adb shell am start -f 0x18000000 -n org.futo.inputmethod.latin.unstable/org.futo.inputmethod.latin.SwipeRecorderActivity --ez replay true --ei beam $beam --ei tries $tries --ei pf $pf | Out-Null
  $ok=$false; for ($i=0;$i -lt 24;$i++){ if ((& $adb shell "test -f $f && echo yes") -match "yes"){$ok=$true;break}; Start-Sleep 5 }
  if ($ok) { break }
}
Start-Sleep 3
& $adb pull $f "$r\donnees\replay_$tag.json" | Out-Null
& $adb logcat -d -s SwipeReplay | Select-String "poids|départ" | Select -Last 2 | % Line
"$tag (tries=$tries) : " + (python "$r\essai_scoring.py" score "$r\donnees\replay_$tag.json")
