#!/bin/sh

run_test() {
        num_job=$1
        directory=$2
        read_type=$3
        run_number=$4
        output="$(fio --name=randread-adbadobenonacdcprod-file --size=217m --io_size=424m --rw=$read_type --directory=$directory --thread=1 --numjobs=$num_job | grep READ | cut -f 2 --delimiter=':' | cut -f 2 --delimiter='(' | cut -f 1 --delimiter='M')"
        echo "$run_number,$num_job,$directory,$read_type,$output"
}

run_number="1"

for i in {1..3} ; do
        num_jobs=( $(shuf -e {"1","2","4","8","12","16","24","32"} ) )
        for num_job in "${num_jobs[@]}"
        do
                read_types=( $(shuf -e {"randread","randread:53"} ) )
                for read_type in "${read_types[@]}"
                do
                        directories=( $(shuf -e "/dir" ) )
                        for directory in "${directories[@]}"
                        do
                                run_test $num_job $directory $read_type $run_number
                                run_number=$((run_number+1))
                        done
                done
        done
done

