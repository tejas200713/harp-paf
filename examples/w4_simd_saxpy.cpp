// SIMD bound: vectorisable single-precision update on L1-resident arrays.
#include <iostream>

static float a[2048], b[2048], c[2048];

int main() {
    for (int i = 0; i < 2048; ++i) {
        b[i] = 1.0f + i * 1e-4f;
        c[i] = 0.5f;
    }
    for (int pass = 0; pass < 3200000; ++pass) {
        float s = 0.999f - (pass & 7) * 0.0001f;
        for (int i = 0; i < 2048; ++i) a[i] = a[i] * s + b[i] * c[i];
    }
    double sum = 0;
    for (int i = 0; i < 2048; ++i) sum += a[i];
    std::cout << "SIMD=" << static_cast<long long>(sum) << "\n";
    return 0;
}
