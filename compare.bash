
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
