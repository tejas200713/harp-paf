// Scalar floating-point bound: dependent square-root / divide chain.
#include <cmath>
#include <iostream>

int main() {
    double x = 3.0;
    for (long i = 0; i < 70000000L; ++i) {
        x = std::sqrt(x * 1.000001 + 2.0) / 1.0000003 + 0.5;
    }
    std::cout << "FP=" << static_cast<long long>(x * 1000000) << "\n";
    return 0;
}
