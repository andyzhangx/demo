$LOG="c:\getprocess.txt"
while ($true)
{
	Get-Process  | Sort-Object -Property VirtualMemorySize -Descending  | Select-Object -First 20 | select-object @{l="Virtual Memory (MB)"; e={$_.VirtualMemorySize/ 1mb}},  @{l="Private Memory (MB)"; e={$_.PrivateMemorySize/ 1mb}}, @{l="Working Set (MB)"; e={$_.WorkingSet/ 1mb}}, Name >> $LOG
	Get-counter -Counter "\memory\% committed bytes in use" >> $LOG
	Sleep 60
}
