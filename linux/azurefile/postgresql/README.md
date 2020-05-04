## Set up a postgresql based on Azure File

```console
kubectl create secret generic foo-db-creds --from-literal username=test --from-literal password="Abc@123"
kubectl create -f https://raw.githubusercontent.com/andyzhangx/demo/master/linux/azurefile/postgresql/postgresql.yaml
```
