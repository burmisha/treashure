#include <cstdlib>
#include <fstream>
#include <iostream>
#include <vector>

using namespace std;

bool thereAreUncheckedTowns(const vector<int>& towns) {
    for (size_t townIndex = 0; townIndex < towns.size(); ++townIndex) {
        if (towns[townIndex] == -1) {
            return true;
        }
    }
    return false;
}

struct Edge {
    const size_t First;
    const size_t Second;
    const size_t Length;
    explicit Edge(size_t first, size_t second, size_t length)
        : First(first)
        , Second(second)
        , Length(length) {
    }
};

int main(int argc, char** argv) {
    cout << "HOWTO build and run: 'clang++ main.cpp -o binary && ./binary'\n";
    cout << "WARNING: All indicies are expected to be zero-based.\n\n";
    ifstream input("input.txt");
    size_t numberOfTowns = 0;
    size_t numberOfRoads = 0;
    input >> numberOfTowns >> numberOfRoads;
    vector<vector<Edge> > edges(numberOfTowns);
    for (size_t i = 0; i < numberOfRoads; ++i) {
        size_t first;
        size_t second;
        size_t length;
        input >> first >> second >> length;
        edges[first].push_back(Edge(first, second, length));
        edges[second].push_back(Edge(second, first, length));
    }

    size_t numberOfCountries = 0;
    input >> numberOfCountries;
    vector<int> towns(numberOfTowns, -1); // -1 is for no country
    for (size_t i = 0; i < numberOfCountries; ++i) {
        size_t country;
        input >> country;
        towns[country] = static_cast<int>(i);
    }
    input.close();

    cout << "Got " << towns.size() << " towns and " << numberOfCountries << " countries.\n";
    cout << "Roads, format is `from: (to1, length1), (to2, length2), ...;':\n";
    for (size_t townIndex = 0; townIndex < edges.size(); ++townIndex) {
        cout << "  Town " << townIndex << ":";
        for (size_t edgeIndex = 0; edgeIndex < edges[townIndex].size(); ++edgeIndex) {
            const Edge& edge = edges[townIndex][edgeIndex];
            cout << " (" << edge.Second << ", " << edge.Length << ")";
        }
        cout << ";\n";
    }

    cout << "\nAdding towns to countries one by one\n";
    size_t currentCountry = 0;
    while (thereAreUncheckedTowns(towns)) {
        cout << "Looking for new town for country " << currentCountry << ". Current state:";
        for (int townIndex = 0; townIndex < towns.size(); ++townIndex) {
            cout << " " << towns[townIndex];
        }
        cout << ".\n";
        int nearestNewTown = -1;
        int minLength = -1;
        for (size_t townIndex = 0; townIndex < towns.size(); ++townIndex) {
            if (towns[townIndex] == currentCountry) {
                cout << "| Country already has town " << townIndex << "\n";
                for (size_t edgeIndex = 0; edgeIndex < edges[townIndex].size(); ++edgeIndex) {
                    const Edge& edge = edges[townIndex][edgeIndex];
                    size_t secondTown = edge.Second;
                    if (towns[secondTown] == -1) {
                        cout << "| | Adjascent town " << secondTown << " is free!\n";
                        size_t length = edge.Length;
                        if ((minLength == -1) || length < static_cast<size_t>(minLength)) {
                            cout << "| | This town is the nearest for now!!! Remember it.\n";
                            minLength = static_cast<int>(length);
                            nearestNewTown = static_cast<int>(secondTown);
                        } else {
                            cout << "| | Not the nearest one\n";
                        }
                    } else {
                        cout << "| | Adjascent town " << secondTown << " is not free.\n";
                    }
                }
            }
        }
        if (nearestNewTown != -1) {
            cout << "L Nearest new town is " << nearestNewTown << " with distance of " << minLength << ", add it.\n";
            towns[static_cast<size_t>(nearestNewTown)] = currentCountry;
        } else {
            cout << "L No new towns at all :-(, try another country.\n";
        }
        currentCountry = (currentCountry + 1) % numberOfCountries;
    }

    cout << "\n";
    cout << "Results:\n";
    for (int countryIndex = 0; countryIndex < numberOfCountries; ++countryIndex) {
        cout << "  Number of country: " << countryIndex << ". Towns list:";
        for (int townIndex = 0; townIndex < towns.size(); ++townIndex) {
            if (towns[townIndex] == countryIndex) {
                cout << " " << townIndex;
            }
        }
        cout << "." << endl;
    }
    return 0;
}
