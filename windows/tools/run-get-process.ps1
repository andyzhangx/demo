$webclient = New-Object System.Net.WebClient
$url = "https://raw.githubusercontent.com/andyzhangx/demo/master/windows/tools/get-process.ps1"
$file = "c:\get-process.ps1"
$webclient.DownloadFile($url, $file)

Start-Process powershell.exe -ArgumentList "-file C:\get-process.ps1" -Windowstyle hidden
