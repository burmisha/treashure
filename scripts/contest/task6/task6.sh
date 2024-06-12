#!/usr/bin/env bash

echo 'digraph "adduser" {
	rankdir=LR;
	node [shape=box];
	"adduser" -> "passwd" [color=blue];
	"adduser" -> "debconf" [color=blue,label="(>= 0.5)"];
	"adduser" [style="setlinewidth(2)"]
	"debconf" [shape=diamond];
	"passwd" [shape=diamond];
}
// total size of all shown packages: 622592
// download size of all shown packages: 155528
' > input.txt

./scripts/contest/task6/task6.py

cat output.txt
