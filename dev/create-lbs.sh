#!/bin/bash

for i in {1..20}
do
	kubectl create service loadbalancer lb$i --tcp=5678:8080
done
