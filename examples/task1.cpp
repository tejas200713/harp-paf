#include <iostream>

int main() {
    long long sum = 0;

    for (int i = 1; i <= 1000000; i++) {
        sum += i;
    }

    std::cout << "SUM=" << sum << std::endl;

    return 0;
}
