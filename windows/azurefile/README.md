# Dynamic Provisioning for azure file on Windows 2016 DataCenter(support from v1.7.x)
## 1. create an azure file storage class
There are two options for creating azure file storage class
#### Option#1: find a suitable storage account that matches ```skuName``` and ```location``` in same resource group when provisioning azure file
download `storageclass-azurefile.yaml` file and modify `skuName`, `location` values
```
kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/storageclass-azurefile.yaml
```

#### Option#2: use existing storage account when provisioning azure file
download `storageclass-azurefile-account.yaml` file and modify `storageAccount` values
```
wget https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/storageclass-azurefile-account.yaml
vi storageclass-azurefile-account.yaml
kubectl create -f storageclass-azurefile-account.yaml
```

## 2. create a pvc for azure file first
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/pvc-azurefile.yaml```

#### make sure pvc is created successfully
```kubectl describe pvc pvc-azurefile```

## 3. create a pod with azure file pvc
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/windows/azurefile/aspnet-pod-azurefile.yaml```

#### watch the status of pod until its `Status` changed from `Pending` to `Running`
```watch kubectl describe po aspnet-azurefile```

## 4. enter the pod container to do validation
```kubectl exec -it aspnet-azurefile -- cmd```

```
C:\>d:
D:\>mkdir test
D:\>cd test
D:\test>dir
 Volume in drive D has no label.
 Volume Serial Number is 50C1-AE52

 Directory of D:\test

09/20/2017  12:40 AM    <DIR>          .
09/20/2017  12:40 AM    <DIR>          ..
               0 File(s)              0 bytes
               2 Dir(s)   5,334,327,296 bytes free
```


# Static Provisioning for azure file on Windows 2016 DataCenter(support from v1.7.x)
## 1. create a secret for azure file
Create an azure file share in the Azure storage account, get the connection info of that azure file and then create a secret that contains the base64 encoded Azure Storage account name and key. In the secret file, base64-encode Azure Storage account name and pair it with name azurestorageaccountname, and base64-encode Azure Storage access key and pair it with name azurestorageaccountkey. For the base64-encode, you could leverage this site: https://www.base64encode.net/

#### 2. download `azure-secrect.yaml` file and modify `azurestorageaccountname`, `azurestorageaccountkey` values
```
wget https://raw.githubusercontent.com/andyzhangx/Demo/master/pv/azure-secrect.yaml
vi azure-secrect.yaml
kubectl create -f azure-secrect.yaml
```

## 3. create a pod with azure file
```kubectl create -f https://raw.githubusercontent.com/andyzhangx/Demo/master/windows/azurefile/aspnet-pod-azurefile.yaml```

#### watch the status of pod until its `Status` changed from `Pending` to `Running`
```watch kubectl describe po aspnet-azurefile```

## 4. enter the pod container to do validation
```kubectl exec -it aspnet-azurefile -- cmd```

```
C:\>d:
D:\>mkdir test
D:\>cd test
D:\test>dir
 Volume in drive D has no label.
 Volume Serial Number is 50C1-AE52

 Directory of D:\test

09/20/2017  12:40 AM    <DIR>          .
09/20/2017  12:40 AM    <DIR>          ..
               0 File(s)              0 bytes
               2 Dir(s)   5,334,327,296 bytes free
```
