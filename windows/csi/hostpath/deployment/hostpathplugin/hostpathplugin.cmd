@echo off
echo %~1, %~2, %~3, %~4 >> c:\var\log\hostpathplugin.log
c:\hostpathplugin.exe %~2 %~3 %~4
