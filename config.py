"""
Cấu hình dùng chung cho toàn bộ dự án.

Mục tiêu:
- Tập trung toàn bộ hyperparameter / tham số quan trọng vào 1 nơi.
- Đảm bảo Apriori và FP-Growth chạy với cùng một bộ ngưỡng lọc để so sánh công bằng.
- Giúp `compare_algorithms.py` và pipeline visualization dùng cấu hình nhất quán.
"""

# Dataset
DATA_PATH = 'data/groceries.csv'

# Ngưỡng mining/rule filtering
MINSUP = 60
MIN_CONF = 0.5
MIN_LIFT = 1.2
MIN_CONVICTION = 1.2

# Tham số tối ưu đếm support (Apriori + hash tree)
HASH_DENOMINATOR = 10

# Visualization flags và giới hạn top-N để biểu đồ dễ đọc
RUN_VISUALIZATIONS = True
TOP_N_ITEMSETS = 20
TOP_N_RULES = 20
TOP_N_NETWORK_RULES = 20
TOP_N_HEATMAP_ITEMS = 15

# Output isolation
APRIORI_OUTPUT_DIR = 'outputs/apriori'
FP_GROWTH_OUTPUT_DIR = 'outputs/fp_growth'

APRIORI_VIS_DIR = 'visualizations/apriori'
FP_GROWTH_VIS_DIR = 'visualizations/fp_growth'

# Benchmark chart (compare_algorithms)
BENCHMARK_VIS_DIR = 'visualizations'
BENCHMARK_PNG_NAME = 'benchmark_performance.png'

