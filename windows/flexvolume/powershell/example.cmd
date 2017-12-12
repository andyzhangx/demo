@echo off
rem need to find a way to pass json parameters which contains "
rem powershell C:\volumeplugins\test~example2.cmd\example.ps1 %*
powershell C:\volumeplugins\test~example2.cmd\example.ps1 %~1 %~2 "test"
