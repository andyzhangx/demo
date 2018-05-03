#!/bin/sh
DIR="/mnt/azurefile"
LOG="/var/log/gitclone.log"

if [ -d "$DIR" ]; then
	if [ "$(ls -A $DIR)" ]; then
		echo "$DIR is empty" >> $LOG
	else
		git clone https://github.com/andyzhangx/kubernetes-drivers.git $DIR 2>&1 >> $LOG
	fi
else
	echo "$DIR does not exist" >> $LOG
fi
