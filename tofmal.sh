#!/usr/bin/env bash

set -ue -o posix -o pipefail

# http://web.archive.org/web/20161026011307/http://tofmal.ru/?xclasses
ALL_CLASSES='
2016а 2016б 2016в 2016г 2016ж 2016к 
2015а 2015б 2015в 2015г 2015ж 2015к 
2014а 2014б 2014в 2014ж 2014к 
2013а 2013б 2013в 2013г 2013ж 2013к 
2012а 2012б 2012в 2012ж 2012к 
2011а 2011б 
2010а 2010в 2010ж 2010к 
2009а 2009б 2009в 2009ж 2009к 
2008а 2008б 2008в 2008г 2008ж 2008к 
2007а 2007б 2007в 2007ж 2007к 
2006а 2006б 2006в 2006д 2006ж 
2005б 2005в 2005г 2005д 2005ж 2005к 
2004б 2004в 2004г 2004д 2004ж 2004к 
2003а 2003б 2003в 2003г 2003е 2003ж 
2002а 2002б 2002в 2002г 2002е 2002ж 
2001а 2001б 2001в 2001г 2001е 2001ж 
2000а 2000б 2000в 2000г 2000д 2000е 
1999б 1999г 1999д 1999е 1999ж 
1998б 1998г 1998д 1998е 
1997б 1997г 1997д 
1996а 1996б 1996в 1996г 
1995а 1995б 1995в 
1994а 1994б 1994в 1994г 
1993а 1993б 1993в 1993г 1993д 
1992а 1992б 1992в 1992г 1992д 
1991а 1991б 1991в 1991г 1991д 
1990а 1990б
'

toEng () {
  echo "${1}" | sed '
    s|а|_A|g;
    s|б|_B|g;
    s|в|_V|g;
    s|г|_G|g;
    s|д|_D|g;
    s|е|_E|g;
    s|ж|_Z|g;
    s|к|_K|g;
  '
}

run () {
  local workDir="${1}"
  cd ${workDir}
  local rawHtmlDir='rawHtml'
  local parsedDataDir='parsedData'
  [ -d ${rawHtmlDir} ] || mkdir ${rawHtmlDir} 
  [ -d ${parsedDataDir} ] || mkdir ${parsedDataDir} 
  echo "Working in ${PWD}: ${rawHtmlDir}, ${parsedDataDir}"
  for class in $(echo ${ALL_CLASSES} | tr -s ' ' '\n' | sort | tail -2); do
    local classEng="$(toEng ${class})"
    local rawFile="${rawHtmlDir}/${classEng}.html"
    # local url="http://tofmal.ru/?${class}"
    # echo "Downloading '${url}' to '${rawFile}'"
    # curl "${url}" -o "${rawFile}"
    # sleep 10
    local parsedFile="${parsedDataDir}/${classEng}.txt"
    local tab="$(printf '\t')"
    iconv -f cp1251 -t utf8 "${rawFile}" \
      | sed  's|<div class=xpupil>|\
|g;
s|</div></div>|\
|g
' \
      | grep 'whereDidLern' \
      | awk 'NR>1' \
      | sed "
        s|<div class=name>||g;
        s|</div><div class=medal>|${tab}|g;
        s|</div><div class=whereDidLern>|${tab}|g;
        s|<img src=../img/gold.png>|GOLD|g;
        s|<img src=../img/silver.png>|SILVER|g;
        s|<img src=../img/best.png>|BEST|g;
      " \
      | sed '
        s|GOLDBEST|GOLD,BEST|g;
        s|SILVERBEST|BEST|g;
      ' | awk -F"\t" '
        BEGIN{print "\"'${classEng}'\": [" }
        {
          print "  {"
          print "    \"fio\": \"u"$1"\","
          print "    \"flags\": \""$2"\","
          print "    \"university\": \"u"$3"\","
          print "  },"
        }
        END{print "],"}
      '
      # > ${parsedFile}
  done
}

run "${HOME}/Dropbox/Lyceum/TofmalRu-classes"
