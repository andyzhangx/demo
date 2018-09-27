$LOG="c:\getprocess.txt"
while ($true)
{
	Get-Process  | Sort-Object -Property PrivateMemorySize -Descending  | Select-Object -First 10 | select-object @{l="Private Memory (MB)"; e={$_.PrivateMemorySize/ 1mb}}, CPU, Name >> $LOG
	Get-counter -Counter "\memory\% committed bytes in use" >> $LOG
	Sleep 60
}
