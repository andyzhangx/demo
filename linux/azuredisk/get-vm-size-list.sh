#!/bin/bash

az account list-locations -o tsv | awk -F '\t' '{print $4}' > locations
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
