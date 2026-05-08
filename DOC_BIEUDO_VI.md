## Tài liệu: Giải thích biểu đồ & các thành phần trong biểu đồ

Tài liệu này giải thích **ý nghĩa các biểu đồ** mà dự án sinh ra trong thư mục `visualizations/` và ý nghĩa **từng thành phần** của mỗi biểu đồ (trục, legend/colorbar, màu sắc, kích thước điểm, nhãn, tooltip, ngưỡng lọc…).

Phạm vi:

- Biểu đồ cho **Apriori**: `visualizations/apriori/`
- Biểu đồ cho **FP-Growth**: `visualizations/fp_growth/`
- Biểu đồ **benchmark** so sánh 2 thuật toán: `visualizations/benchmark/`

Các ngưỡng (lọc luật) và giới hạn top-N để biểu đồ dễ đọc nằm trong `config.py`:

- `MINSUP`: ngưỡng **support count** tối thiểu khi khai phá itemsets
- `MIN_CONF`, `MIN_LIFT`, `MIN_CONVICTION`: ngưỡng lọc luật
- `TOP_N_ITEMSETS`, `TOP_N_RULES`, `TOP_N_NETWORK_RULES`, `TOP_N_HEATMAP_ITEMS`: giới hạn số phần tử đưa lên biểu đồ

---

### 1) Thuật ngữ/metric dùng trong biểu đồ (cốt lõi cần nắm)

- **Support count**: số transaction có chứa một itemset (hoặc \(X \cup Y\) của một luật).
- **Support (chuẩn hoá 0..1)**: \(\text{support}(X) = \frac{\text{support\_count}(X)}{N}\), với \(N\) là tổng transaction.
- **Confidence**: \(\text{conf}(X \to Y) = \frac{\text{support}(X \cup Y)}{\text{support}(X)}\). Có thể hiểu là “khi đã mua \(X\), xác suất mua thêm \(Y\)”.
- **Lift**: \(\text{lift}(X \to Y) = \frac{\text{conf}(X \to Y)}{\text{support}(Y)}\).
  - \(> 1\): liên hệ dương (mua kèm mạnh hơn ngẫu nhiên)
  - \(= 1\): gần như độc lập
  - \(< 1\): liên hệ âm
- **Conviction**: \(\text{conv}(X \to Y) = \frac{1-\text{support}(Y)}{1-\text{conf}(X \to Y)}\).
  - Conviction càng cao thường càng “kéo theo” mạnh theo hướng \(X\) làm tăng khả năng có \(Y\).
  - Nếu `confidence = 1` thì conviction có thể thành `inf` (vô cùng).

Gợi ý đọc nhanh:

- **Luật “tốt” để đề xuất hành động** thường có: confidence cao, lift > 1 rõ rệt, conviction cao và support không quá nhỏ.
- **Support cao nhưng lift ≈ 1**: thường chỉ phản ánh item phổ biến (chưa chắc có quan hệ nhân quả/giá trị gợi ý).

---

### 2) Nhóm biểu đồ: Frequent Itemsets (Top nhóm sản phẩm hay đi chung)

#### 2.1. Bar chart tĩnh (PNG)

- **File**:
  - `visualizations/apriori/static/frequent_itemsets_bar.png`
  - `visualizations/fp_growth/static/frequent_itemsets_bar.png`
- **Dữ liệu đầu vào**: top frequent itemsets theo `support_count` (mặc định `TOP_N_ITEMSETS=20`).
- **Mục đích**: cho biết “nhóm sản phẩm nào thường xuất hiện nhất trong giỏ hàng”.

Thành phần trong biểu đồ:

- **Trục X**: `Support Count` (số lần xuất hiện).
  - Thanh càng dài → itemset xuất hiện càng nhiều.
- **Trục Y**: tên itemset (nhóm sản phẩm).
  - Vì tên có thể dài, bản PNG có thể bị cắt ngắn bằng dấu `...` (chỉ cắt cho hiển thị).
- **Màu thanh**: chỉ là thẩm mỹ (không mã hoá thêm metric nào khác trong bản PNG).
- **Tiêu đề**: mô tả nội dung “Top nhóm sản phẩm thường được mua cùng nhau”.

Cách đọc/diễn giải:

- Các thanh top đầu thường là các mặt hàng “cực phổ biến” (vd `whole milk`, `other vegetables` trong Groceries).
- Nếu 2-itemset đứng cao (vd “A, B”) → A và B hay cùng xuất hiện; tuy nhiên “hay cùng xuất hiện” chưa đủ để kết luận “kéo theo” (cần xem luật + lift/confidence).

#### 2.2. Bar chart tương tác (HTML)

- **File**:
  - `visualizations/apriori/interactive/frequent_itemsets_bar.html`
  - `visualizations/fp_growth/interactive/frequent_itemsets_bar.html`

Thành phần quan trọng:

- **Tooltip khi hover** hiển thị:
  - itemset đầy đủ (không bị cắt)
  - `Support count`
  - `Support` (chuẩn hoá)

Khi nào nên dùng HTML thay vì PNG:

- Khi itemset dài và bạn cần đọc đúng tên đầy đủ.
- Khi muốn xem chính xác support (0..1) thay vì chỉ nhìn xếp hạng.

---

### 3) Nhóm biểu đồ: Association Rules — Scatter “bản đồ chất lượng luật”

#### 3.1. Scatter tĩnh (PNG)

- **File**:
  - `visualizations/apriori/static/rules_scatter.png`
  - `visualizations/fp_growth/static/rules_scatter.png`
- **Dữ liệu đầu vào**: top rules theo tiêu chí “ưu tiên confidence, lift, support” (mặc định `TOP_N_RULES=20`).
- **Mục đích**: nhìn 1 lần để thấy “luật nào mạnh”, “phân bố luật ra sao”.

Quy ước mã hoá (quan trọng nhất):

- **Trục X**: `Support` của luật (support của \(X \cup Y\)).
- **Trục Y**: `Confidence` của luật.
- **Kích thước điểm**: `Lift` (điểm càng to → lift càng cao).
- **Màu điểm**: `Conviction` (đi kèm **colorbar**).

Các thành phần trong biểu đồ:

- **Colorbar (thanh màu)**: ghi “Conviction”.
  - Màu theo thang `viridis`: thường “sáng hơn” ~ giá trị lớn hơn (tuỳ dải).
- **Viền điểm (edgecolors)**: giúp phân biệt điểm khi chồng lên nhau.
- **Tiêu đề phụ**: gợi ý “góc trên cùng bên phải” là nơi tập trung luật mạnh (support cao hơn + confidence cao).

Cách đọc/diễn giải (mẹo thực tế):

- **Góc trên bên phải** (support ↑, confidence ↑): luật vừa xuất hiện đủ nhiều, vừa “đúng” nhiều lần → thường đáng ưu tiên.
- **Điểm to**: lift cao → quan hệ mạnh hơn ngẫu nhiên, bớt rơi vào bẫy “item phổ biến”.
- **Màu theo conviction**: conviction cao thường củng cố rằng luật “kéo theo” rõ.
- **Support thấp nhưng confidence/lift cao**: có thể là “insight niche” (ngách) — phù hợp nếu bạn target nhóm nhỏ/chiến dịch cụ thể.

#### 3.2. Scatter tương tác (HTML)

- **File**:
  - `visualizations/apriori/interactive/rules_scatter.html`
  - `visualizations/fp_growth/interactive/rules_scatter.html`

Thành phần quan trọng:

- **Tooltip khi hover** hiển thị đầy đủ:
  - Luật: `antecedent -> consequent`
  - Support, Confidence, Lift, Conviction
- **Zoom/Pan**: xem cụm điểm bị chồng lên nhau.
- **Colorbar**: conviction (giống PNG) nhưng đọc giá trị dễ hơn qua tooltip.

---

### 4) Nhóm biểu đồ: Scatter “Luật vàng” (highlight top đề xuất)

- **File**:
  - `visualizations/apriori/interactive/rules_scatter_golden.html`
  - `visualizations/fp_growth/interactive/rules_scatter_golden.html`
- **Mục đích**: thuyết trình/demo nhanh, nhấn mạnh “Top luật đề xuất” so với phần còn lại.

Thành phần trong biểu đồ:

- **Hai nhóm điểm (legend)**:
  - `Toàn bộ luật`: màu xám (bối cảnh)
  - `Luật vàng (Top)`: màu đỏ (điểm nhấn)
- **Trục X/Y**: Support / Confidence
- **Tooltip**: luật + lift + conviction

“Luật vàng” được chọn như thế nào:

- Hệ thống chấm điểm tổng hợp ưu tiên:
  - confidence cao
  - support đủ lớn
  - lift cao
  - conviction cao (trường hợp `inf` được ưu tiên rất mạnh)

File đi kèm (đọc nhanh top luật):

- `visualizations/apriori/insights/golden_rules.txt`
- `visualizations/fp_growth/insights/golden_rules.txt`

---

### 5) Nhóm biểu đồ: Network graph “luồng hành vi mua sắm”

#### 5.1. Network graph tĩnh (PNG)

- **File**:
  - `visualizations/apriori/static/rules_network.png`
  - `visualizations/fp_growth/static/rules_network.png`
- **Dữ liệu đầu vào**: top rules ưu tiên lift cao (mặc định `TOP_N_NETWORK_RULES=20`) để mạng không quá rối.
- **Mục đích**: xem các mối liên hệ **item → item** dưới dạng mạng (node/edge), nhận diện cụm sản phẩm và “hướng” mua kèm.

Định nghĩa node/cạnh:

- **Node**: một item (một mặt hàng).
- **Cạnh có hướng (mũi tên)**: từ item ở vế trái (antecedent) sang item ở vế phải (consequent).
  - Nếu một luật có nhiều item ở mỗi vế, hệ thống “bung” ra thành nhiều cạnh item-item.

Quy ước mã hoá (PNG):

- **Độ dày cạnh**: theo `Confidence` (cạnh càng dày → xác suất kéo theo càng cao).
- **Màu cạnh**: theo `Lift` (có colormap `plasma`; màu “nóng/sáng” hơn thường ~ lift cao hơn).
- **Kích thước node**: cố định (bản PNG), chủ yếu để đọc nhãn.
- **Layout**: spring layout (tự động kéo các node liên quan gần nhau).

Cách đọc/diễn giải:

- **Nhìn cụm**: các node gần nhau và nhiều cạnh qua lại thường là “nhóm sản phẩm” liên quan.
- **Nhìn mũi tên**: gợi ý hướng gợi ý cross-sell:
  - Ví dụ \(A \to B\) mạnh → khi khách chọn A, có thể gợi ý B.
- **Cạnh dày + màu mạnh**: vừa dễ xảy ra (confidence cao) vừa “không ngẫu nhiên” (lift cao).

#### 5.2. Network graph tương tác (HTML)

- **File**:
  - `visualizations/apriori/interactive/rules_network.html`
  - `visualizations/fp_growth/interactive/rules_network.html`

Thành phần quan trọng:

- **Tooltip trên node**: tên item + `Degree` (bậc node; node càng “trung tâm” degree càng cao).
- **Tooltip trên cạnh** (thực hiện bằng marker ở giữa cạnh):
  - Support, Confidence, Lift, Conviction
- **Colorbar**: Lift (trong HTML).
- **Kích thước node**: tăng theo `Degree` (node trung tâm to hơn).

Khi nào nên dùng HTML:

- Khi mạng dày, PNG khó đọc nhãn/đường.
- Khi cần xem chính xác metric của từng cạnh.

---

### 6) Nhóm biểu đồ: Heatmap “bản đồ nhiệt lift giữa các mặt hàng”

#### 6.1. Heatmap tĩnh (PNG)

- **File**:
  - `visualizations/apriori/static/rules_heatmap.png`
  - `visualizations/fp_growth/static/rules_heatmap.png`
- **Dữ liệu đầu vào**: top rules (giống scatter), nhưng heatmap chỉ giữ lại **top-N item** theo tổng điểm lift (mặc định `TOP_N_HEATMAP_ITEMS=15`) để ma trận không quá lớn.
- **Mục đích**: nhìn nhanh cặp item nào có **liên kết mạnh nhất** (theo lift).

Ý nghĩa trục:

- **Trục X**: vế phải (Consequents)
- **Trục Y**: vế trái (Antecedents)

Ý nghĩa từng ô:

- Giá trị trong ô là **Lift lớn nhất** quan sát được cho cặp (antecedent item, consequent item) trong các rule đang xét.
- Màu “nóng/sáng” hơn (colormap `magma`) → lift cao hơn.

Cách đọc/diễn giải:

- Tìm các “ô sáng” nổi bật → các cặp A→B có lift cao.
- Đừng chỉ nhìn màu: cặp lift cao nhưng support rất thấp có thể khó áp dụng đại trà (xem thêm tooltip ở HTML).

#### 6.2. Heatmap tương tác (HTML)

- **File**:
  - `visualizations/apriori/interactive/rules_heatmap.html`
  - `visualizations/fp_growth/interactive/rules_heatmap.html`

Tooltip khi hover hiển thị:

- Vế trái (Y), vế phải (X)
- Support, Confidence, Lift, Conviction

Khi nào nên dùng HTML:

- Khi bạn cần đọc chính xác “cặp nào mạnh vì lift cao nhưng support thấp/ cao”.
- Khi muốn lọc insight theo mục tiêu: ưu tiên lift hay ưu tiên support.

---

### 7) Nhóm biểu đồ benchmark (so sánh Apriori vs FP-Growth)

Các biểu đồ benchmark nằm ở `visualizations/benchmark/`:

#### 7.1. `benchmark_time_stacked.png` — cột chồng thời gian

- **Mục đích**: tách “Mining time” và “Rule generation time”.
- **Trục X**: thuật toán (`Apriori`, `FP-Growth`)
- **Trục Y**: thời gian (giây)
- **Hai phần màu trong mỗi cột**:
  - **Mining Time**: thời gian khai phá frequent itemsets
  - **Rule Generation Time**: thời gian sinh luật từ itemsets
- **Nhãn số trên đỉnh cột**: tổng thời gian (mining + rule).

Cách đọc nhanh:

- Nếu phần Mining của Apriori cao hơn nhiều → Apriori bị “nặng” ở bước sinh & đếm candidate.
- Rule generation thường gần nhau vì đều cần duyệt/tách từ frequent itemsets (tuỳ cấu hình).

#### 7.2. `benchmark_memory_nodes.png` — so sánh “không gian” bằng số node

- **Mục đích**: so sánh độ “phình” cấu trúc dữ liệu (ước lượng chi phí RAM/duyệt).
- **Trục X**: loại cấu trúc:
  - `Apriori (HashTree)`
  - `FP-Growth (FPTree)`
- **Trục Y**: tổng số node (ước lượng)
- **Nhãn số trên cột**: số node.

Lưu ý diễn giải:

- Node nhiều hơn **không luôn** đồng nghĩa chạy chậm hơn, nhưng thường gợi ý tốn RAM hơn và traversal nhiều hơn.
- Với dataset này FP-tree có thể nhiều node nhưng vẫn nhanh do tránh sinh candidate theo từng level như Apriori.

#### 7.3. `benchmark_scalability_line.png` — đường scalability theo MINSUP

- **Mục đích**: xem thời gian tổng thay đổi thế nào khi bài toán “khó dần”.
- **Trục X**: `MINSUP (support count)` và bị đảo ngược (minsup càng nhỏ → càng khó).
- **Trục Y**: tổng thời gian chạy (giây).
- **Legend**: hai đường `Apriori`, `FP-Growth`.

Cách đọc nhanh:

- Nếu đường Apriori tăng rất nhanh khi MINSUP giảm → Apriori nhạy với việc bùng nổ candidate.
- Nếu FP-Growth ổn định hơn → FP-tree khai thác nén dữ liệu tốt hơn khi ngưỡng minsup thấp.

---

### 8) Liên kết giữa “structured outputs” và biểu đồ

Nếu bạn muốn tự vẽ lại hoặc kiểm chứng số liệu, dữ liệu nguồn của biểu đồ nằm ở:

- `outputs/apriori/structured/frequent_itemsets.csv`
- `outputs/apriori/structured/association_rules.csv`
- `outputs/fp_growth/structured/frequent_itemsets.csv`
- `outputs/fp_growth/structured/association_rules.csv`
- `outputs/comparison/algorithm_comparison.csv`

Ý nghĩa một số cột hay gặp:

- **Frequent itemsets**:
  - `itemset_label`: tên itemset dạng chuỗi (vd `"other vegetables, whole milk"`)
  - `itemset_size`: số item trong itemset
  - `support_count`: số lần xuất hiện
  - `support`: support chuẩn hoá
- **Association rules** (tuỳ file nhưng logic giống nhau):
  - `antecedent_label`, `consequent_label`: nhãn luật
  - `rule_support` (hoặc `support`): support chuẩn hoá của luật
  - `confidence`, `lift`, `conviction`: các metric

---

### 9) Checklist viết báo cáo (gợi ý bạn có thể copy vào report)

- **Frequent itemsets bar chart**:
  - Nêu top 5 itemset phổ biến nhất + diễn giải “thói quen mua sắm phổ biến”.
- **Rule scatter plot**:
  - Chọn 3–5 điểm ở “góc trên bên phải” và đọc tooltip (support/conf/lift/conviction) để viết nhận xét.
  - Nhắc rõ quy ước: \(x=\)support, \(y=\)confidence, size=lift, color=conviction.
- **Heatmap**:
  - Nêu 3 ô sáng nhất (A→B) và đối chiếu lại luật tương ứng trong `golden_rules.txt` hoặc `association_rules.csv`.
- **Network graph**:
  - Chỉ ra 1–2 node trung tâm (degree cao) và 2–3 hướng cross-sell đáng chú ý.
- **Benchmark**:
  - Nhận xét xu hướng: FP-Growth nhanh hơn ở mining; Apriori tăng nhanh khi minsup giảm.

