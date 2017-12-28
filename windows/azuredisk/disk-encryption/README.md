### Eanble Azure Disk Encryption on Windows Server Core
According to [Azure Disk Encryption troubleshooting guide - Windows Server 2016 Server Core](https://docs.microsoft.com/en-us/azure/security/azure-security-disk-encryption-tsg#troubleshooting-windows-server-2016-server-core):
#### 1. Eanble bdehdcfg component on Windows Server Core
1) open a powershell window
```
start powershell
```
2) Download bdehdcfg and 7zip component 
```
mkdir c:\tmp
cd c:\tmp
$webclient = New-Object System.Net.WebClient
$url = "https://github.com/andyzhangx/Demo/raw/master/windows/azuredisk/disk-encryption/bdehdcfg.zip"
$file = "$pwd\bdehdcfg.zip"
$webclient.DownloadFile($url,$file)

$url = "http://www.7-zip.org/a/7z1701-x64.exe"
$file = "$pwd\7zip.exe"
$webclient.DownloadFile($url,$file)
```
3) Install 7zip to `c:\tmp` directory and Unzip `bdehdcfg` component
```
.\7zip.exe
.\7z.exe x .\bdehdcfg.zip 
mv .\bdehdcfg\* c:\windows\system32\
mv .\bdehdcfg\en-us\* c:\windows\system32\en-us\
```

4) Install `bdehdcfg` component and reboot VM
```
cd c:\windows\system32\
bdehdcfg.exe -target default
```

#### 2. Enable Azure Disk Encryption on Windows Server Core VM
```
az keyvault set-policy -n KEYVAULT-NAME --spn aad-client-id --key-permissions wrapKey --secret-permissions set
az vm encryption enable -g RESOURCE-GROUP-NAME -n VM-NAME --aad-client-id aad-client-id --aad-client-secret aad-client-secret --disk-encryption-keyvault KEYVAULT-NAME --volume-type all
```

#### 3. If above command completes successsfully, use below command line to check encryption status:
```
az vm encryption show -g RESOURCE-GROUP-NAME -n VM-NAME
```

```
{
  "dataDisk": "Encrypted",
  "osDisk": "Encrypted",
  "osDiskEncryptionSettings": {
    "diskEncryptionKey": {
      "secretUrl": "https://KEYVAULT-NAME.vault.azure.net/secrets/722BE9AE-2F9D-43DF-8E41-57EC88FCDCAF/0571cbb2175b4ded99f262e48d0ba348",
      "sourceVault": {
        "id": "/subscriptions/{subs-id}/resourceGroups/{resource-group-name}/providers/Microsoft.KeyVault/vaults/{keyvault-name}"
      }
    },
    "enabled": true,
    "keyEncryptionKey": null
  },
  "osType": "Windows",
  "progressMessage": "https://KEYVAULT-NAME.vault.azure.net/secrets/722BE9AE-2F9D-43DF-8E41-57EC88FCDCAF/0571cbb2175b4ded99f262e48d0ba348"
}
```

#### Links

