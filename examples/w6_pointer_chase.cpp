// Memory-latency bound: dependent random loads through a 32 MiB cycle.
#include <cstdint>
#include <iostream>
#include <vector>

int main() {
    std::vector<uint32_t> next(8u << 20);
    for (uint32_t i = 0; i < next.size(); ++i) next[i] = i;
    uint64_t state = 42;
    for (uint32_t i = next.size() - 1; i > 0; --i) {
        state = state * 6364136223846793005ull + 1442695040888963407ull;
        uint32_t j = (state >> 17) % i;
        uint32_t t = next[i]; next[i] = next[j]; next[j] = t;
    }
    uint32_t p = 0;
    uint64_t sum = 0;
    for (long i = 0; i < 7000000L; ++i) {
        p = next[p];
        sum += p;
    }
    std::cout << "CHASE=" << sum << "\n";
    return 0;
}
