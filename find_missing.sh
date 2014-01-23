#!/usr/bin/env bash
set -x
set -e
workdir="/Users/burmisha/github"

function find_diff () {
	name_re=$1
	name_id=$2
	echo $name_re
	
	backup="$workdir/backup_$name_id.lst"
	current="$workdir/current_$name_id.lst"
	diff="$workdir/diff_$name_id.lst"

	b_dir="/Volumes/BurMi320/backup_2012-02-28/Photo"
	c_dir="/Volumes/tosh_1tb/Photo"
	
	(cd $b_dir && find . -name $name_re) | sort >$backup
	(cd $c_dir && find . -name $name_re) | sort >$current
	
	join -v 1 $backup $current >$diff
	rm $backup $current

	>$diff.found
	# for f in $(cat $diff); do
	cat $diff | while read -d $'\n' f; do
		m=$(cat "$b_dir/$f" | md5)
		# find /Volumes/tosh_1tb/Photo -name _MG_4736.CR2 | while read -sd $'\n' i; do echo $i; done
		find $c_dir -name "$(basename $f)" | while read -d $'\n' ff; do
			mm=$(cat "$ff" | md5)
			if [[ $m == $mm ]]; then
				echo $f >>$diff.found
			fi
		done 
		# exit 0
	done
	join -v 1 $diff $diff.found >$diff.not_found

}

cd $workdir
# find_diff '*.CR2' "CR2"
# find_diff '*.DNG' "DNG"
# find_diff '*.dng' "dng_sm"
find_diff '*.JPG' "JPG"
find_diff '*.jpg' "jpg_sm"
