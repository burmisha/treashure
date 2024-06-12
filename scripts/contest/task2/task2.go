package main

import (
    "bufio"
    "fmt"
    "os"
    "strconv"
    "log"
)

func main() {
    numbers := readInput()
    result := int64(12)
    if len(numbers) == 2 {
        result = numbers[0] + numbers[1]
    }

    if err := os.WriteFile("output.txt", []byte(fmt.Sprintf("%d\n", result)), 0666); err != nil {
        log.Fatal(err)
    }
}

func readInput() []int64 {
    f, err := os.Open("input.txt")
    if err != nil {
        log.Fatal(err)
    }
    defer f.Close()

    var numbers []int64
    scanner := bufio.NewScanner(f)
    scanner.Split(bufio.ScanWords)
    for scanner.Scan() {
        number, _ := strconv.ParseInt(scanner.Text(), 10, 64)
        numbers = append(numbers, number)
    }
    return numbers
}
