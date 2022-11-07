
get_all_sums () {
  workdir="$1"
  find "${workdir}" -type f \
    | sort \
    | while read line; do
        md5sum "${line}"
      done \
    | sed "s|*${workdir}||g;s| |\t|" 
}

compare_dirs () {
  first="$1"
  second="$2"
  mkdir -p /d/tmp && cd $_
  # get_all_sums "${first}" > first.sums &
  # get_all_sums "${second}" > second.sums &
  # wait; wait;
  awk -vF="\t" -vIFS="\t" -vFS="\t" -vOFS="\t" '
    BEGIN{while (getline < "first.sums") {first[$2]=$1}}
    { 
      filename=$2
      second[filename]=$1
      if (!first[filename]) {
        print "Appeared: "filename
      } else {
        if (first[filename] != $1) {
          print "Changed: "filename
        }
      }
    }
    END{
      for (filename in first) {
        if (!second[filename]) {
          print "Vanished: "filename
        }
      }
    }
  ' second.sums \
    | sort
  # ( 
  #   get_all_sums "${first}"
  #   get_all_sums "${second}"
  # ) | sort | uniq -u
  # files="${workdir}/first.lst ${workdir}/second.lst"
  
  # echo "Vanished: $(join -v1 ${files} | wc -l)"
  # echo "Appeared: $(join -v2 ${files} | wc -l)"
  # join ${files} | awk '$2!=$3'
}

# compare_dirs '/d/PhotoBook' '/H/PhotoBook'
# compare_dirs '/e/Тетя Оля' '/H/Тетя Оля'
# compare_dirs '/d/LRcats_old' '/H/LRcats_old'
# compare_dirs '/e/video' '/H/video'
# compare_dirs '/d/PhotoPhotoshop' '/H/PhotoPhotoshop'
compare_dirs '/d/Photo' '/H/Photo'
# compare_dirs '/d/tmp/a' '/d/tmp/b'


list_files () {
  local dirname="${1}"
  local dstfile="${2}"
  cd ${dirname}
  find . -type f | wc -l | awk '{print "Found "$1" files in '${dirname}'"}'
  # find . -type f > "${dstfile}"
  find . -type f -exec md5 '{}' \; > ${dstfile}
  sort "${dstfile}" -o "${dstfile}"
  sed -e 's|MD5 (.*) = ||g' "${dstfile}" ${dstfile} | sort | uniq -c | sort -k1,1rn > ${dstfile}.md5
  cd -
}

compare () {
  local macbookDir="${1}"
  local backupDir="${2}"

  list_files ${macbookDir} ~/macbook.txt
  list_files ${backupDir} ~/backup.txt

  diff ~/macbook.txt ~/backup.txt > ~/diff.txt 
  head -20 ~/diff.txt 
  wc ~/macbook.txt ~/backup.txt
  grep '^>' ~/diff.txt | wc -l | awk '{print "Backup has "$1" more files"}'
  grep '^<' ~/diff.txt | wc -l | awk '{print "Backup is missing "$1" files"}'
  diff ~/macbook.txt.md5 ~/backup.txt.md5
}

# cp -r /Users/burmisha/Documents/Zoom /Volumes/tosh2tb/MacBackup_2020-09/Zoom
compare /Users/burmisha/Documents/Zoom /Volumes/tosh2tb/MacBackup_2020-09/Zoom
# rm -r /Users/burmisha/Documents/Zoom.broken.path

compare /Users/burmisha/PhotoLocal /Volumes/tosh2tb/MacBackup_2020-09/PhotoLocal

compare /Users/burmisha/Downloads /Volumes/tosh2tb/MacBackup_2020-09/Downloads
compare /Users/burmisha/tmp /Volumes/tosh2tb/MacBackup_2020-09/tmp
compare /Users/burmisha/video /Volumes/tosh2tb/MacBackup_2020-09/video

grep 60749ec6a25f49ca5488bbd5fc8d445c ~/macbook.txt ~/backup.txt
grep 359fd342409d4be515a7cb534d24f375 ~/macbook.txt ~/backup.txt
grep 1f4b21f0677476530632291503b9a447 ~/macbook.txt ~/backup.txt
grep 78b900a2cf616cfb79b477d4ab961b5f ~/macbook.txt ~/backup.txt
grep a69f20a9547439f8778f2c77789e3d55 ~/macbook.txt ~/backup.txt
