#!/bin/bash

# Scenario#1: create keyvault, key, and DiskEncryptionSet
rgName=
location=southcentralus 
keyVaultName=
keyName=
diskEncryptionSetName=

az group create -g $rgName -l $location
az keyvault create -n $keyVaultName -g $rgName -l $location --enable-purge-protection true --enable-soft-delete true
az keyvault key create --vault-name $keyVaultName -n $keyName --protection software
keyVaultId=$(az keyvault show --name $keyVaultName --query [id] -o tsv)
keyVaultKeyUrl=$(az keyvault key show --vault-name $keyVaultName --name $keyName --query key.kid -o tsv)
az disk-encryption-set create -n $diskEncryptionSetName -g $rgName --key-url $keyVaultKeyUrl --source-vault $keyVaultId -l $location
# copy down the DiskEncryptionSet id from the output
desIdentity=$(az ad sp list --display-name $diskEncryptionSetName --query [].objectId -o tsv)
az keyvault set-policy -n $keyVaultName -g $rgName --object-id $desIdentity --key-permissions wrapkey unwrapkey get
az role assignment create --assignee $desIdentity --role Reader --scope $keyVaultId

# Scenario#2: key rotation
keyName=	#input new key name here

az keyvault key create --vault-name $keyVaultName -n $keyName --protection software
keyVaultKeyUrl=$(az keyvault key show --vault-name $keyVaultName --name $keyName --query key.kid -o tsv)

az disk-encryption-set update -n $diskEncryptionSetName -g $rgName --key-url $keyVaultKeyUrl --source-vault $keyVaultId
