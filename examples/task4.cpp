#include <iostream>
#include <cmath>

int main() {
    volatile double result = 0.0;

    for (int i = 1; i <= 1000000; i++) {
        result = result + std::sqrt(static_cast<double>(i));
    }

    std::cout << "TASK4=" << static_cast<long long>(result) << "\n";
    return 0;
}
