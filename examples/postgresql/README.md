## Run a postgresql pod based on azure disk

```
kubectl create secret generic foo-db-creds --from-literal username=xiazhang --from-literal password="User@123"
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/examples/postgresql/postgresql-azuredisk.yaml
```

 - Note:

the permission of azure file is set in the mounting moment, after that, azure file permission could not be changed. So for postgres container, it **could not run on azure file**.
In stead, you could use azure disk, I have tried it works well. And pls note that if you mount azure disk directly `mountPath: /var/lib/postgresql/data`, it will fail either with following error:
```
nitdb: directory "/var/lib/postgresql/data" exists but is not emptyIt contains a lost+found directory, perhaps due to it being a mount point
```
Instead, use `subPath` will work, it will create a new directory in the new azure disk.

So here is the two key places that make this config work
 - use azure disk instead of azure file
```
kind: StorageClass
apiVersion: storage.k8s.io/v1
metadata:
  name: footestdb
provisioner: kubernetes.io/azure-disk
parameters:
  skuName: Standard_LRS
  kind: Managed
  cachingmode: None
```

 - use subPath (it will create a new directory in the newly attached azure disk)
```
        volumeMounts:
        - mountPath: /var/lib/postgresql/
          subPath: data
          name: footestdb
```

- related issue:
[Persistent Volume Claim permissions](https://github.com/Azure/AKS/issues/225)
