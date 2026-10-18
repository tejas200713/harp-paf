
#include <iostream>

int add(int a, int b) {
    return a + b;
}

int multiply(int a, int b) {
    return a * b;
}

int main() {
    std::cout << "Addition: " << add(5, 3) << "\n";
    std::cout << "Multiplication: " << multiply(5, 3) << "\n";
    return 0;
}
