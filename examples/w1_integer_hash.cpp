// Integer ALU and multiplier bound: xorshift hashing.
#include <cstdint>
#include <iostream>

int main() {
    uint64_t x = 88172645463325252ull, acc = 0;
    for (long i = 0; i < 430000000L; ++i) {
        x ^= x << 13;
        x ^= x >> 7;
        x ^= x << 17;
        acc += x * 0x9E3779B97F4A7C15ull;
        acc ^= acc >> 29;
    }
    std::cout << "HASH=" << acc << "\n";
    return 0;
}
