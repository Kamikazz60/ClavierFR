param([string]$words="doanh,coucou",[string]$tag="x",[string]$learn="",[string]$forget="")
$r="C:\Users\Doanh\Desktop\Programme IA\clavierPers"; $adb="C:\Users\Doanh\AppData\Local\Android\Sdk\platform-tools\adb.exe"
$f="/sdcard/Android/data/org.futo.inputmethod.latin.unstable/files/synth_last.json"
for ($try=0; $try -lt 3; $try++) {
  & $adb shell rm -f $f
  & $adb shell am start -f 0x18000000 -n org.futo.inputmethod.latin.unstable/org.futo.inputmethod.latin.SwipeRecorderActivity --ez replay true --es synth $words $(if ($learn) { '--es'; 'learn'; $learn }) $(if ($forget) { '--es'; 'forget'; $forget }) | Out-Null
  $ok=$false; for ($i=0;$i -lt 24;$i++){ if ((& $adb shell "test -f $f && echo yes") -match "yes"){$ok=$true;break}; Start-Sleep 4 }
  if ($ok) { break }
}
Start-Sleep 2
& $adb pull $f "$r\donnees\synth_$tag.json" | Out-Null
$j = Get-Content "$r\donnees\synth_$tag.json" -Raw -Encoding utf8 | ConvertFrom-Json
"tries=$($j.tries)"; $j.results | % { "$($_.word) -> $($_.results -join ' | ')" }
