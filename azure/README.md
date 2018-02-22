## Azure specific k8s issues
 - VM status inconsistency issue
 Problem:
 
 Solution:
 ```
 $vm = Get-AzureRMVM -ResourceGroupName $rg -Name $vmname  
 Update-AzureRmVM -ResourceGroupName $rg -VM $vm -verbose -debug
 ```
