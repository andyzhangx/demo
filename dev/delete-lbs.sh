#!/bin/bash

for i in {1..20}
do
	kubectl delete service lb$i --wait=false
done
