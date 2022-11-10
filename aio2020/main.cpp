// Mikhail Burmistrov, burmisha.com, i.like.spam@ya.ru, 2020
#include <algorithm>
#include <fstream>
#include <unordered_map>
#include <string>
#include <vector>

typedef std::string word_t;
typedef unsigned long int counter_t;
typedef std::unordered_map<word_t, counter_t> frequency_t;
typedef std::pair<word_t, counter_t> word_frequency_t;


int main(int argc, char** argv) {
    if (argc != 3) {
        throw std::invalid_argument("Expected 2 arguments after binary name");
    }
    // unordered_map, ибо map - это дерево и там log
    // старое чтение без потоков, std::ifstream::get делает много всего с локалью и кучу проверок, в 2 раза за 8–10 строк
    // std::string - терпимо
    // isalpha и tolower — дико тормозят
    // unordered_map.reserve — ещё
    // отказаться от stl
    // написать на Go Hello World
    // https://yadi.sk/d/xTFWy38y3GBAgS

    // https://github.com/shodanium/freq

    int length = 65536;
    char * buffer = new char [length];

    std::ifstream input(argv[1]);
    frequency_t frequency;

    // read chars, form words, count occurrences
    word_t word("");
    char c;
    while (input) {
        input.read(buffer, length);
        for (size_t i = 0; i < input.gcount(); ++i) {
            char c = buffer[i];
            if (isalpha(c)) {
                word.append(1, static_cast<char>(tolower(c)));
            } else if (!word.empty()) {
                auto it = frequency.find(word);
                if (it != frequency.end()) {
                    it->second += 1;
                } else {
                    frequency.insert(word_frequency_t(word, 1));
                }
                word.clear();
            }
        }
    }
    input.close();

    // sort occurrences
    std::vector<word_frequency_t> frequency_vector;
    for (const auto& it : frequency) {
        frequency_vector.push_back(it);
    }
    auto compare = [](word_frequency_t const & a, word_frequency_t const & b) { 
        return (a.second > b.second) || ((a.second == b.second) && a.first < b.first);
    };
    std::sort(frequency_vector.begin(), frequency_vector.end(), compare);

    // print occurrences
    std::ofstream output;
    output.open(argv[2], std::ofstream::out);    
    char buf[64];  // enough for counter
    for (const auto& it : frequency_vector) {
        sprintf(buf, "%4lu", it.second);
        output << buf << " " << it.first << '\n';
    }
    output.close();
    return 0;
}
