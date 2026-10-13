#include <iostream>
#include <vector>

int main() {
    const int N = 100000;
    std::vector<int> data(N);

    for (int i = 0; i < N; i++) {
        data[i] = (i * 37) % 1000;
    }

    long long sum = 0;
    for (int value : data) {
        sum += value;
    }

    std::cout << "TASK3=" << sum << "\n";
    return 0;
}
