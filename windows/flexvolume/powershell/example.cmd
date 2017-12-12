@echo off
rem need to find a better way to pass json parameters which contains "
rem powershell C:\volumeplugins\test~example.cmd\example.ps1 %*
powershell C:\volumeplugins\test~example.cmd\example.ps1 %~1 %~2 '%~3' '%~4'
