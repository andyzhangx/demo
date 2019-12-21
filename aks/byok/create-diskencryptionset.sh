#!/bin/bash

subscriptionId=
rgName=andy-diskencryptionset 
location=northeurope 
keyVaultName=andy-des
keyName=andy-des
diskEncryptionSetName=andy-des

az group create -g $rgName -l $location
az account set --subscription $subscriptionId
az keyvault create -n $keyVaultName -g $rgName -l $location --enable-purge-protection true --enable-soft-delete true
az keyvault key create --vault-name $keyVaultName -n $keyName --protection software
keyVaultId=$(az keyvault show --name $keyVaultName --query [id] -o tsv)
keyVaultKeyUrl=$(az keyvault key show --vault-name $keyVaultName --name $keyName --query key.kid -o tsv)
az group deployment create -g $rgName --template-uri "https://raw.githubusercontent.com/ramankumarlive/manageddiskscmkpreview/master/CreateDiskEncryptionSet.json" --parameters "diskEncryptionSetName=$diskEncryptionSetName" "keyVaultId=$keyVaultId" "keyVaultKeyUrl=$keyVaultKeyUrl" "region=$location"
desIdentity=$(az ad sp list --display-name $diskEncryptionSetName --query [].objectId -o tsv)
az keyvault set-policy -n $keyVaultName -g $rgName --object-id $desIdentity --key-permissions wrapkey unwrapkey get
az role assignment create --assignee $desIdentity --role Reader --scope $keyVaultId
