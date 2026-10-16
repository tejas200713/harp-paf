// Multi-phase workload: compute phase, streaming phase, then branchy phase.
#include <cstdint>
#include <iostream>
#include <vector>

__attribute__((noinline)) static uint64_t left(uint64_t a, uint64_t v) { return a * 31 + v; }
__attribute__((noinline)) static uint64_t right(uint64_t a, uint64_t v) { return (a >> 3) ^ (v * 7919); }

int main() {
    uint64_t x = 88172645463325252ull, acc = 0;
    for (long i = 0; i < 300000000L; ++i) {          // phase 1: integer ALU
        x ^= x << 13; x ^= x >> 7; x ^= x << 17;
        acc += x * 0x9E3779B97F4A7C15ull;
    }
    std::vector<uint64_t> data(8u << 20, 1);
    for (int pass = 0; pass < 20; ++pass)            // phase 2: memory stream
        for (size_t i = 0; i < data.size(); ++i) { acc += data[i]; data[i] = acc; }
    uint64_t state = 7;
    for (long i = 0; i < 80000000L; ++i) {           // phase 3: branches
        state = state * 6364136223846793005ull + 1442695040888963407ull;
        uint64_t v = state >> 17;
        acc = (v & 1) ? left(acc, v) : right(acc, v);
    }
    std::cout << "PHASED=" << acc << "\n";
    return 0;
}
