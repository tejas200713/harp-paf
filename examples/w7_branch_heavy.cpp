// Branch-prediction bound: data-dependent, unpredictable control flow.
#include <cstdint>
#include <iostream>

__attribute__((noinline)) static uint64_t left(uint64_t a, uint64_t v) { return a * 31 + v; }
__attribute__((noinline)) static uint64_t right(uint64_t a, uint64_t v) { return (a >> 3) ^ (v * 7919); }

int main() {
    uint64_t state = 7, acc = 0;
    for (long i = 0; i < 150000000L; ++i) {
        state = state * 6364136223846793005ull + 1442695040888963407ull;
        uint64_t v = state >> 17;
        acc = (v & 1) ? left(acc, v) : right(acc, v);
    }
    std::cout << "BRANCH=" << acc << "\n";
    return 0;
}
