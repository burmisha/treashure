#!/usr/bin/env bash
# Mikhail Burmistrov, burmisha.com, i.like.spam@ya.ru, 2020
clang++ -O2 -std=c++11 -Wc++11-extensions main.cpp -o aio2020

# echo 'The time has come, the Walrus said,
# to talk of many things...
# ' > in.txt
# ./aio2020 in.txt out.txt
# cat out.txt

head -1000000 pg.txt > pg1m.txt
time ./aio2020 pg1m.txt out.txt

# echo -e '\nMore examples:'
# echo '#2' && echo '' >in2.txt && ./aio2020 in2.txt out2.txt && cat out2.txt
# echo '#3' && echo ' ' >in3.txt && ./aio2020 in3.txt out3.txt && cat out3.txt
# echo '#4' && echo -e ' ' >in4.txt && ./aio2020 in4.txt out4.txt && cat out4.txt
# echo '#5' && echo -e 'b a b a ab' >in5.txt && ./aio2020 in5.txt out5.txt && cat out5.txt
# echo '#6' && echo -e 'b a b a b ab' >in6.txt && ./aio2020 in6.txt out6.txt && cat out6.txt
# echo '#7' && echo -e 'b a b a a ab' >in7.txt && ./aio2020 in7.txt out7.txt && cat out7.txt
# echo '#8' && echo -e 'b a b a a ba' >in8.txt && ./aio2020 in8.txt out8.txt && cat out8.txt
# echo '#9' && echo -e 'B A A B b abba' >in9.txt && ./aio2020 in9.txt out9.txt && cat out9.txt
# echo '#10' && echo -e '«a»;&**\x00a' >in10.txt && ./aio2020 in10.txt out10.txt && cat out10.txt
# echo '#11' && echo -e '«a»;&**\x00aa' >in11.txt && ./aio2020 in11.txt out11.txt && cat out11.txt
# echo '#12' && yes yes | head -2000000 >in12.txt && ./aio2020 in12.txt out12.txt && cat out12.txt
# echo '#13' && cat /dev/random | head >in13.txt && ./aio2020 in13.txt out13.txt && cat out13.txt
# echo '#14' && echo 'a' >'in14.txt' && echo 'b' > 'out14.txt' && ./aio2020 'in14.txt' 'out14.txt' && cat 'out14.txt'

# echo -e '\nCompare time (takes up to 30 seconds on MBP 2015)'
# N=20000000
# yes no | head -${N} >in_time1.txt
# yes no | head -${N} >in_time2.txt
# time ./aio2020 in_time1.txt out_time.txt
# time uniq -c in_time2.txt
# time wc in_time1.txt
# time wc in_time1.txt
# time wc in_time2.txt
