Function Usage()
{
    Write-Output "Usage: "
    Write-Output "       .\example.ps1 init"
    Write-Output "       .\example.ps1 mount"
    Write-Output "       .\example.ps1 unmount"	
}

Function Init()
{
	Write-Output '{"status": "Success", "capabilities": {"attach": false}}'
}

function DoMount
{
    param (
        [Parameter(Mandatory)]
        [string] $MountDir,
		[Parameter(Mandatory)]
        [string] $JsonParameters		
    )
	#Write-Output ("MountDir: $MountDir, JsonParameters: $JsonParameters")
	md $MountDir > $null
	if ($?) {
		Write-Output '{"status": "Success"}'
	} else {
		Write-Output '{"status": "Failure"}'
	}
}

Function UnMount()
{
    param (
        [Parameter(Mandatory)]
        [string] $MountDir,
		[Parameter(Mandatory)]
        [string] $JsonParameters		
    )
	#Write-Output ("MountDir: $MountDir, JsonParameters: $JsonParameters")
	rm -r -force $MountDir > $null
	if ($?) {
		Write-Output '{"status": "Success"}'
	} else {
		Write-Output '{"status": "Failure"}'
	}
}

#Common usage:
#   .\example.ps1 init
#   .\example.ps1 mount mountDir jsonParameters
#   .\example.ps1 unmount unmountDir jsonParameters

$command = $args[0].ToLower()
if ($command -eq "init"){
	Init
}
elseif ($command -eq "mount"){
	if ($args.Length -gt 2){
		DoMount $args[1] "'$($args[2])'"
	} else {
		Usage
	}
}
elseif ($command -eq "unmount"){
	if ($args.Length -gt 2){
		UnMount $args[1] "'$($args[2])'"
	} else {
		Usage
	}
}
else
{
    Usage
}
