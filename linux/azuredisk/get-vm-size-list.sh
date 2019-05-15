#!/bin/bash

for location in `cat ./locations`
do
	az vm list-sizes -l $location -o tsv | awk -F '\t' '{print "\""$3"\":"$1","}' | sort | uniq > $location.txt
done

cat *.txt > vmsizelist.data
cat vmsizelist.data | sort | uniq > vmsizelist.final
