#Login-AzureRmAccount
#Get-AzureRmSubscription
#Select-AzureRmSubscription -SubscriptionName "..."

#You may run "Set-ExecutionPolicy Unrestricted" in admini mode in advance
# .\install-getprocess-ext-on-all-windows-nodes.ps1 -ResourceGroupPrefix pull-kubernetes-e2e-win -Dryrun $false

[CmdletBinding()]
Param(
  [Parameter(Mandatory=$True,Position=1)]
   [string]$ResourceGroupPrefix,
	
   [Parameter(Mandatory=$false)]
   [bool]$Dryrun = $true
)

$groups = Get-AzureRmResourceGroup
for ($i=0; $i -lt $groups.length; $i++) {
	$rg_name = $groups[$i].ResourceGroupName
	if (! $rg_name.StartsWith($ResourceGroupPrefix, "CurrentCultureIgnoreCase")) {
		echo "skip $rg_name with prefix $ResourceGroupPrefix..."
		continue
	}
	$vms = Get-AzureRmVM -ResourceGroupName $rg_name
	for ($j=0; $j -lt $vms.length; $j++) {
		if ($vms[$j].StorageProfile.OsDisk.OsType.ToString() -eq "Windows") {
			$vm_name = $vms[$j].Name
			$location = $vms[$j].Location
			
			if ( $Dryrun ) {
				echo "Dryrun on $vm_name, resource group: $rg_name"
			}
			else {
				for ($k=0; $k -lt 4; $k++) {
					$extension_name = "cse-agent-$k"
					echo "remove original $extension_name on $vm_name, resource group: $rg_name"
					Remove-AzurermVMCustomScriptExtension -ResourceGroupName $rg_name -VMName $vm_name -Name $extension_name -force
				}
				echo "set get-process CustomScriptExtension on $vm_name, resource group: $rg_name, location: $location"
				Set-AzureRmVMCustomScriptExtension -ResourceGroupName $rg_name `
					-VMName $vm_name -Name "get-process" `
					-FileUri "https://raw.githubusercontent.com/andyzhangx/demo/master/windows/tools/run-get-process.ps1" `
					-Run "run-get-process.ps1" -Location $location		
			}
		}
	}	
}
