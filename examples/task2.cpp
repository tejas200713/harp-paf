#include <iostream>

int main() {
    volatile long long result = 0;
    for (long long i = 1; i <= 3000000; i++) {
        result = result + (i % 97);
    }
    std::cout << "TASK2=" << result << "\n";
    return 0;
}
