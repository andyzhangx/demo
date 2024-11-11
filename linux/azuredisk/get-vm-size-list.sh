#!/bin/bash

az account set -s 8ecadfc9-d1a3-4ea4-b844-0d9f87e4d7c8
#az account list-locations -o tsv | awk -F '\t' '{print $4}' > locations
for location in `cat ./locations`
do
	echo "get vm list-sizes on $location region ..."
	az vm list-sizes -l $location -o tsv | awk -F '\t' '{print "\""$3"\":"$1","}' | sort | uniq > $location.txt
done

cat *.txt > vmsizelist.data
OUTPUT="vmsizelist.final"
cat vmsizelist.data | sort | uniq > $OUTPUT
sed -i 'y/abcdefghijklmnopqrstuvwxyz/ABCDEFGHIJKLMNOPQRSTUVWXYZ/' $OUTPUT

echo "got all vm list-sizes from all regions, output file: $OUTPUT"
