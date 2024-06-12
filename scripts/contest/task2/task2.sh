#!/usr/bin/env bash

echo 2 2 > input.txt
go run ./scripts/contest/task2/task2.go
cat output.txt

echo 57 43 > input.txt
go run ./scripts/contest/task2/task2.go
cat output.txt

echo 123456789 673243342 > input.txt
go run ./scripts/contest/task2/task2.go
cat output.txt

echo  > input.txt
go run ./scripts/contest/task2/task2.go
cat output.txt

