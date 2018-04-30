#!/bin/sh
BASE="/mnt/"
LOG="/var/log/genfiles.log"

for dirname in ` ls $BASE `
do
        dir=$BASE/$dirname
        if [ "$(ls -A $dir)" ]; then
                echo "$dir is not empty" >> $LOG
        else
                git clone https://github.com/andyzhangx/demo.git $dir 2>&1 >> $LOG
        fi
done
