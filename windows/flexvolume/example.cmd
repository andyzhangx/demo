@echo off
rem '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
rem   File Name:
rem       example.cmd
rem 
rem   Abstract:
rem       This script is an example script using flexvolume on Windows node, it will do
rem 	  1. mount: make a mount directory
rem 	  2. unmount: remove the mount directory
rem   Note: This is a FlexVolume Driver Without Master-initiated Attach/Detach
rem '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

if "%~1"=="init" goto init
if "%~1"=="mount" goto mount
if "%~1"=="unmount" goto unmount

:usage

echo example.cmd init
echo example.cmd mount [mount dir] [mount device] [json params]
echo example.cmd unmount [unmount dir]

goto :eof

:init
@echo {"status": "Success", "capabilities": {"attach": false}}
goto :eof

:mount
@echo "mount", %~2, %~3, %~4 >> c:\k\example.log
md %~2
@echo {"status": "Success"}
goto :eof

:unmount
@echo "unmount", %~2, %~3, %~4 >> c:\k\example.log
rm -rf %~2
