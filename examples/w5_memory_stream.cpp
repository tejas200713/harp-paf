// Memory-bandwidth bound: sequential read-modify-write over 64 MiB.
#include <cstdint>
#include <iostream>
#include <vector>

int main() {
    std::vector<uint64_t> data(8u << 20, 1);
    uint64_t acc = 0;
    for (int pass = 0; pass < 120; ++pass) {
        for (size_t i = 0; i < data.size(); ++i) {
            acc += data[i];
            data[i] = acc;
        }
    }
    std::cout << "STREAM=" << acc << "\n";
    return 0;
}
