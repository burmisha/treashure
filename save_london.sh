#!/usr/bin/env bash
set -e
set -x 

disk="/Volumes/tosh_1tb"
backup="$disk/backup_2013-09-21/London"
current="$disk/PhotoCatalogs/London"

workdir="$disk/save_london"
filetype="JPG"
cur_files="$workdir/current_$filetype.lst"
bu_files="$workdir/backup_$filetype.lst"

mkdir -p $workdir
cd $workdir

find $backup -name "*.$filetype" -exec md5 '{}' ';' | sed -e 's|^MD5 (\(.*\)) = \(.*\)$|\1   \2|g' >$bu_files  
find $current -name "*.$filetype" -exec md5 '{}' ';' | sed -e 's|^MD5 (\(.*\)) = \(.*\)$|\1   \2|g' >$cur_files  

regex="$(echo "(2013-0(7-(29|30|31)|8-(0|1[012345])))" | sed 'sa\([()|-]\)a\\\1ag')"

cat $cur_files $bu_files \
  | grep $regex \
  | sort -k2,2 \
  | uniq -f 1 -u \
  | sort


