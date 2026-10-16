// HARP-PAF stressor and training kernels.
//
// Compile one kernel per binary:  g++ -O2 -std=c++17 -DKERNEL=<id> ...
// Run:  ./kernel            -> runs until killed (interference probing)
//       ./kernel <units>    -> runs <units> work units and exits (training)
//
// Each kernel saturates mainly one shared resource of an SMT core.

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <vector>

#ifndef KERNEL
#error "Compile with -DKERNEL=<id>"
#endif

static volatile uint64_t sink;

static inline uint64_t lcg(uint64_t &state) {
    state = state * 6364136223846793005ull + 1442695040888963407ull;
    return state >> 17;
}

#if KERNEL == 1  // int: integer ALU and multiplier
static uint64_t unit(uint64_t acc) {
    uint64_t x = acc | 1;
    for (int i = 0; i < (1 << 20); ++i) {
        x ^= x << 13; x ^= x >> 7; x ^= x << 17;
        acc += x * 0x9E3779B97F4A7C15ull;
        acc ^= acc >> 29;
    }
    return acc;
}
#elif KERNEL == 2  // div: integer divider
static uint64_t unit(uint64_t acc) {
    uint64_t d = (acc & 0xFF) + 3;
    for (int i = 0; i < (1 << 18); ++i) {
        acc = acc / d + (acc % d) + 0x12345678ull + i;
        d = (acc & 0xFF) + 3;
    }
    return acc;
}
#elif KERNEL == 3  // fp: scalar FP divide / square root chain
static uint64_t unit(uint64_t acc) {
    double x = 1.0 + (acc & 0xFF);
    for (int i = 0; i < (1 << 18); ++i) {
        x = std::sqrt(x * 1.000001 + 2.0) / 1.0000003 + 0.5;
    }
    return acc + static_cast<uint64_t>(x);
}
#elif KERNEL == 4  // simd: vectorisable FP over L1-resident arrays
static float va[2048], vb[2048], vc[2048];
static uint64_t unit(uint64_t acc) {
    if (vb[0] == 0.0f)
        for (int i = 0; i < 2048; ++i) { vb[i] = 1.0f + i * 1e-4f; vc[i] = 0.5f; }
    for (int pass = 0; pass < 2048; ++pass) {
        float s = 0.999f - (pass & 7) * 0.0001f;  // converges, no overflow
        for (int i = 0; i < 2048; ++i) va[i] = va[i] * s + vb[i] * vc[i];
    }
    return acc + static_cast<uint64_t>(va[acc & 2047]);
}
#elif KERNEL == 5  // stream: sequential memory bandwidth (64 MiB)
static std::vector<uint64_t> &buffer() {
    static std::vector<uint64_t> data(8u << 20, 1);
    return data;
}
static uint64_t unit(uint64_t acc) {
    auto &data = buffer();
    for (size_t i = 0; i < data.size(); ++i) {
        acc += data[i];
        data[i] = acc;
    }
    return acc;
}
#elif KERNEL == 6  // chase: dependent random loads (32 MiB, latency bound)
static std::vector<uint32_t> &chain() {
    static std::vector<uint32_t> next = [] {
        std::vector<uint32_t> v(8u << 20);
        for (uint32_t i = 0; i < v.size(); ++i) v[i] = i;
        uint64_t state = 42;
        for (uint32_t i = v.size() - 1; i > 0; --i) {  // Sattolo: one cycle
            uint32_t j = lcg(state) % i;
            uint32_t t = v[i]; v[i] = v[j]; v[j] = t;
        }
        return v;
    }();
    return next;
}
static uint64_t unit(uint64_t acc) {
    auto &next = chain();
    uint32_t p = acc % next.size();
    for (int i = 0; i < (1 << 20); ++i) p = next[p];
    return acc + p;
}
#elif KERNEL == 7  // cache: random read-modify-write in a 2 MiB working set
static std::vector<uint64_t> &buffer() {
    static std::vector<uint64_t> data(256u << 10, 3);
    return data;
}
static uint64_t unit(uint64_t acc) {
    auto &data = buffer();
    uint64_t state = acc | 1;
    for (int i = 0; i < (1 << 20); ++i) {
        uint64_t &slot = data[lcg(state) & (data.size() - 1)];
        slot += acc;
        acc ^= slot;
    }
    return acc;
}
#elif KERNEL == 8  // branch: data-dependent, unpredictable branches
__attribute__((noinline)) static uint64_t left(uint64_t a, uint64_t v) { return a * 31 + v; }
__attribute__((noinline)) static uint64_t right(uint64_t a, uint64_t v) { return (a >> 3) ^ (v * 7919); }
static uint64_t unit(uint64_t acc) {
    uint64_t state = acc | 1;
    for (int i = 0; i < (1 << 20); ++i) {
        uint64_t v = lcg(state);
        acc = (v & 1) ? left(acc, v) : right(acc, v);
    }
    return acc;
}
#elif KERNEL == 9  // l1: L1-resident loads with high IPC
static uint64_t small[512];
static uint64_t unit(uint64_t acc) {
    for (int i = 0; i < (1 << 20); ++i) acc += small[i & 511] + (acc >> 7);
    small[acc & 511] = acc;
    return acc;
}
#elif KERNEL == 10  // phased: compute phase, then streaming phase
static std::vector<uint64_t> &buffer() {
    static std::vector<uint64_t> data(4u << 20, 1);
    return data;
}
static uint64_t unit(uint64_t acc) {
    uint64_t x = acc | 1;
    for (int i = 0; i < (1 << 28); ++i) {
        x ^= x << 13; x ^= x >> 7; x ^= x << 17;
        acc += x;
    }
    auto &data = buffer();
    for (int pass = 0; pass < 8; ++pass)
        for (size_t i = 0; i < data.size(); ++i) { acc += data[i]; data[i] = acc; }
    return acc;
}
#else
#error "Unknown KERNEL id"
#endif

int main(int argc, char **argv) {
    uint64_t acc = 0x2545F4914F6CDD1Dull;

    if (argc < 2) {
        for (;;) sink = acc = unit(acc);
    }

    long units = std::strtol(argv[1], nullptr, 10);
    for (long i = 0; i < units; ++i) acc = unit(acc);
    std::printf("KERNEL=%llu\n", static_cast<unsigned long long>(acc));
    return 0;
}
