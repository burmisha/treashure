package main

import (
    "bufio"
    "fmt"
    "os"
    "strconv"
)

func main() {
    numbers := readInput()
    result := int64(12)
    if len(numbers) == 2 {
        result = numbers[0] + numbers[1]
    }
    fmt.Printf("%d\n", result)
}

func readInput() []int64 {
    var numbers []int64
    scanner := bufio.NewScanner(os.Stdin)
    scanner.Split(bufio.ScanWords)
    for scanner.Scan() {
        number, _ := strconv.ParseInt(scanner.Text(), 10, 64)
        numbers = append(numbers, number)
    }
    return numbers
}
