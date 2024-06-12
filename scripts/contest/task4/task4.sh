#!/usr/bin/env bash

echo 'ab
aabbccd' > input.txt

./scripts/contest/task4/task4.py

cat output.txt
