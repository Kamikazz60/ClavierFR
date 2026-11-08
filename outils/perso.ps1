param([bool]$on=$true)
$adb="C:\Users\Doanh\AppData\Local\Android\Sdk\platform-tools\adb.exe"
$v = if ($on) { "true" } else { "false" }
& $adb shell am start -f 0x18000000 -n org.futo.inputmethod.latin.unstable/org.futo.inputmethod.latin.SwipeRecorderActivity --ez personalize $v | Out-Null
Start-Sleep 3
& $adb shell "run-as org.futo.inputmethod.latin.unstable grep -i personalized shared_prefs/org.futo.inputmethod.latin.unstable_preferences.xml"
