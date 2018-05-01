#!/bin/sh
BASE="/mnt"
LOG="/var/log/genfiles.log"

for dirname in ` ls $BASE `
do
        dir=$BASE/$dirname
        if [ -d $dir ]; then
            echo "begin to generate files under $dir ..." >> $LOG
            size=1024
            while [ $size -lt 10485760 ]
            do
                output_file=$dir/$size
                if [ ! -f "$output_file" ]; then
                    dd if=/dev/zero of=$output_file bs=1024 count=$size >> $LOG 2>&1
                fi
                size=$(( $size * 4 ))
            done
        fi
done
