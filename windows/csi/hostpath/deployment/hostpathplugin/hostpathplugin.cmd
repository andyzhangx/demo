@echo off
echo %~1, %~2, %~3, %~4, %~5, %~6 >> c:\hostpathplugin.log
c:\hostpathplugin.exe %~1"="%~2 %~3"="%~4 %~5"="%~6
