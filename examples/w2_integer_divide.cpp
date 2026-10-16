// Integer divider bound: dependent 64-bit division and modulo.
#include <cstdint>
#include <iostream>

int main() {
    uint64_t acc = 1234567, d = 7;
    for (long i = 0; i < 120000000L; ++i) {
        acc = acc / d + (acc % d) + 0x12345678ull + i;
        d = (acc & 0xFF) + 3;
    }
    std::cout << "DIV=" << acc << "\n";
    return 0;
}
