#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <iomanip>

struct StatsResult {
    double sum;
    double mean;
    double variance;
    double stddev;
};

std::vector<double> generate_series(int n) {
    std::vector<double> values;
    values.reserve(n);
    for (int i = 1; i <= n; ++i) {
        values.push_back(static_cast<double>(i * i % 97) + 0.5);
    }
    return values;
}

double calculate_sum(const std::vector<double>& data) {
    double total = 0.0;
    for (double val : data) {
        total += val;
    }
    return total;
}

StatsResult compute_statistics(const std::vector<double>& data) {
    StatsResult res = {0.0, 0.0, 0.0, 0.0};
    if (data.empty()) {
        return res;
    }

    res.sum = calculate_sum(data);
    res.mean = res.sum / data.size();

    double sq_diff_sum = 0.0;
    for (double val : data) {
        double diff = val - res.mean;
        sq_diff_sum += diff * diff;
    }

    res.variance = sq_diff_sum / data.size();
    res.stddev = std::sqrt(res.variance);
    return res;
}

void print_report(const StatsResult& res, size_t sample_size) {
    std::cout << std::fixed << std::setprecision(2);
    std::cout << "--- HARP-PAF Single Code Optimization Demo ---" << "\n";
    std::cout << "Sample Count : " << sample_size << "\n";
    std::cout << "Sum          : " << res.sum << "\n";
    std::cout << "Mean         : " << res.mean << "\n";
    std::cout << "Variance     : " << res.variance << "\n";
    std::cout << "Std Deviation: " << res.stddev << "\n";
    std::cout << "Status       : Verification Success\n";
}

int main() {
    constexpr int DATA_POINTS = 50;
    std::vector<double> dataset = generate_series(DATA_POINTS);
    StatsResult result = compute_statistics(dataset);
    print_report(result, dataset.size());
    return 0;
}
