@echo off
echo %~1, %~2, %~3, %~4 >> c:\driver-registrar.log
c:\driver-registrar.exe %~1"="%~2 %~3"="%~4
