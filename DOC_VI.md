## Tài liệu dự án: Association Rule Mining (Apriori + Hash Tree)

Tài liệu này mô tả **cách chạy** và **cách hoạt động nội bộ** của dự án theo đúng trình tự thực thi: từ lúc khởi động script đến khi sinh xong **frequent itemsets** và **association rules**.

### 1) Tổng quan nhanh

- **Mục tiêu**: khai phá luật kết hợp (Association Rule Mining) từ dữ liệu giỏ hàng (market basket).
- **Thuật toán chính**: **Apriori** để sinh tập phổ biến (frequent itemsets).
- **Tối ưu đếm support**: dùng **Hash Tree** (thay vì brute force duyệt mọi candidate trên mọi transaction).
- **Thước đo luật**: **support**, **confidence**, **lift**, **conviction**; rule hiện được lọc đồng thời theo `MIN_CONF`, `MIN_LIFT`, `MIN_CONVICTION`.

Các file chính:

- `arm.py`: entrypoint + toàn bộ pipeline (load data → Apriori → rules → output + structured export + visualization).
- `hash_tree.py`: cấu trúc `Tree/Node` cho hash tree + hàm sinh subset `generate_subsets`.
- `timing_wrapper.py`: decorator `@timeit` để in thời gian chạy.
- `visualize.py`: module dựng biểu đồ PNG và HTML từ structured outputs.
- `fp_growth.py`: pipeline FP-Growth (FP-tree) + sinh rule + xuất output/visualization riêng.
- `compare_algorithms.py`: benchmark so sánh Apriori vs FP-Growth và sinh ảnh benchmark.
- `config.py`: file cấu hình dùng chung cho cả 2 thuật toán và benchmark.
- `data/groceries.csv`: dữ liệu giao dịch.
- `outputs/*`: kết quả xuất ra theo từng thuật toán.

### 2) Cách khởi động (run)

Tại thư mục gốc dự án, chạy:

```bash
python arm.py
```

Script sẽ:

- đọc `data/groceries.csv`
- tạo mapping item → số nguyên và lưu `reverse_map.pkl`
- chạy Apriori để tạo `l_final.pkl` (danh sách frequent itemsets theo từng \(k\))
- sinh luật kết hợp và tính các metric chuẩn của association rule
- ghi file kết quả vào thư mục `outputs/apriori/`
- ghi structured outputs vào `outputs/apriori/structured/`
- ghi biểu đồ vào `visualizations/apriori/`

Chạy FP-Growth:

```bash
python fp_growth.py
```

Kết quả tương ứng:

- `outputs/fp_growth/`
- `outputs/fp_growth/structured/`
- `visualizations/fp_growth/`

Chạy benchmark:

```bash
python compare_algorithms.py
```

- báo cáo so sánh nằm ở `outputs/comparison/`
- ảnh benchmark nằm ở `visualizations/benchmark_performance.png`

### 3) Các tham số cấu hình quan trọng

Các biến cấu hình hiện được gom về `config.py` để cả Apriori và FP-Growth dùng chung:

- **`MINSUP`**: ngưỡng **support count** tối thiểu (đang dùng `60`).
  - Lưu ý: code so sánh `> MINSUP` (lớn hơn), không phải `>=`.
- **`MIN_CONF`**: ngưỡng confidence tối thiểu (đang dùng `0.5`).
  - Lưu ý: code so sánh `> MIN_CONF` (lớn hơn), không phải `>=`.
  - Đây là một trong ba ngưỡng lọc rule.
- **`MIN_LIFT`**: ngưỡng lift tối thiểu (đang dùng `1.2`).
  - Chỉ giữ các luật có độ phụ thuộc dương rõ ràng hơn trạng thái độc lập.
- **`MIN_CONVICTION`**: ngưỡng conviction tối thiểu (đang dùng `1.2`).
  - Chỉ giữ các luật có mức độ kéo theo đủ mạnh.
- **`HASH_DENOMINATOR`**: mẫu số \(k\) của hàm băm dạng `x mod k` trong hash tree (đang dùng `10`).
- **`RUN_VISUALIZATIONS`**: bật/tắt bước sinh biểu đồ sau khi mining xong.
- **`TOP_N_ITEMSETS`**: số frequent itemsets dùng cho bar chart.
- **`TOP_N_RULES`**: số rules dùng cho scatter plot.
- **`TOP_N_NETWORK_RULES`**: số rules mạnh nhất dùng cho network graph.
- **`TOP_N_HEATMAP_ITEMS`**: số item mạnh nhất được giữ lại để dựng heatmap.

### 4) Trình tự thực thi chi tiết (từ start đến finish)

Phần này bám sát `if __name__ == '__main__':` trong `arm.py`.

#### 4.1. Chọn đường dẫn dữ liệu

Trong `arm.py`:

- `data_path = 'data/groceries.csv'`

Mỗi dòng (row) trong CSV được hiểu là **một transaction**, gồm danh sách item.

#### 4.2. Load dữ liệu (đọc CSV) — `load_data(path)`

Hàm `load_data` trong `arm.py` (được bọc `@timeit`):

- dùng `csv.reader` đọc toàn bộ file thành `transactions` (list các list item dạng string)
- gom toàn bộ item xuất hiện, lấy `set` để có danh sách **unique items**, rồi `sorted`

Đầu ra:

- `transactions`: `List[List[str]]`
- `items`: `List[str]` (unique)

#### 4.3. Tạo mapping item ↔ integer — `create_map(items)` + `applymap(...)`

Trong Apriori, thao tác trên số nguyên thường nhanh hơn thao tác trên chuỗi:

- `create_map(items)` tạo:
  - `map_`: `item(str) -> id(int)`
  - `reverse_map`: `id(int) -> item(str)`
- `reverse_map` được lưu ra file `reverse_map.pkl` để khi xuất kết quả có thể đổi ngược id → tên item.
- `applymap(transaction, map_)` chuyển từng item trong transaction sang id.

Tại `frequent_itemset_generation`:

- `one_itemset = [[itemset] for itemset in items]` tạo các 1-itemset ở dạng list-of-list
- `items_mapped = [applymap(itemset, map_) for itemset in one_itemset]`
  - trở thành `[[id0], [id1], ...]`
- `transactions_mapped = [applymap(transaction, map_) for transaction in transactions]`

#### 4.4. Apriori: tạo `L1`, rồi lặp tạo `C(k+1)` và lọc thành `L(k+1)`

Tất cả nằm trong `frequent_itemset_generation(data_path)`.

##### Bước A — Đếm support cho 1-itemset để tạo `L1`

- gọi `subset(items_mapped, transactions_mapped)` để lấy `candidate_counts`
- lọc theo ngưỡng `MINSUP` để tạo `l_current` (dictionary):
  - key: `tuple(itemset)` (vd `(12,)`)
  - value: `support_count` (số lần itemset xuất hiện trong các transaction)
- `L_final` là list chứa các `Lk` theo thứ tự \(k = 1, 2, ...\)
  - `L_final[0]` là `L1`
  - `L_final[1]` là `L2`, ...

##### Bước B — Sinh candidate `C(k+1)` từ `Lk` bằng `apriori_gen(l_prev)`

Hàm `apriori_gen` trong `arm.py` thực hiện join step theo tinh thần Apriori:

- duyệt mọi cặp itemset trong `l_prev`
- nếu `temp_a[:-1] == temp_b[:-1]` thì join để tạo candidate mới
- sort candidate để chuẩn hóa

Kết quả: `c_current` (list các candidate itemset kích thước \(k+1\)).

##### Bước C — Đếm support cho candidate bằng `subset(c_current, transactions_mapped)`

Đây là phần tối ưu quan trọng: **không brute force** check subset theo kiểu `set(candidate).issubset(set(transaction))` cho mọi candidate, mà dùng **hash tree**.

- `subset(c_list, transactions)` trong `arm.py`:
  - tạo `t = Tree(c_list, k=HASH_DENOMINATOR, max_leaf_size=100)`
  - với mỗi `transaction`:
    - sinh tất cả các subset độ dài đúng bằng độ dài candidate (kích thước \(k\)) bằng `generate_subsets(transaction, len(c_list[0]))`
    - với mỗi subset `sub`: `t.check(sub, update=True)` để tăng đếm trong tree nếu subset này đúng là 1 candidate đã insert
  - sau đó, với mỗi candidate trong `c_list`:
    - lấy support count bằng `t.check(candidate, update=False)`

##### Bước D — Lọc theo `MINSUP` để được `L(k+1)` và lặp tiếp

- `C_t` là dict support counts của candidate
- lọc `> MINSUP` để tạo `l_current` mới
- nếu `l_current` rỗng thì dừng

##### Bước E — Lưu kết quả frequent itemsets

Kết thúc, `L_final` được pickle ra file:

- `l_final.pkl`

> Trong code có khối comment cho phép load nhanh từ `l_final.pkl` nếu muốn bỏ qua bước tính lại.

#### 4.5. Sinh luật kết hợp và tính metric — `generate_rules(frequent_items, total_transactions)`

Đầu vào:

- `frequent_items` chính là `L_final` (list các dict \(L1, L2, ...\))

Ý tưởng:

- Với mỗi frequent itemset \(I\) có kích thước \(k \ge 2\), sinh các cách tách:
  - \(X = I \setminus Y\)
  - \(Y\) là consequent (vế phải)
- Tính:
  - \(\text{support}(X \to Y) = \text{support}(X \cup Y)\)
  - \(\text{confidence}(X \to Y) = \frac{\text{support}(X \cup Y)}{\text{support}(X)}\)
  - \(\text{lift}(X \to Y) = \frac{\text{confidence}(X \to Y)}{\text{support}(Y)}\)
  - \(\text{conviction}(X \to Y) = \frac{1 - \text{support}(Y)}{1 - \text{confidence}(X \to Y)}\)

Trong bản cập nhật này, code tách riêng phần tính metric vào hàm `calculate_rule_metrics(...)` trong `arm.py`. Hàm này nhận:

- support count của toàn bộ itemset \(X \cup Y\)
- support count của antecedent \(X\)
- support count của consequent \(Y\)
- tổng số transaction

Từ đó quy đổi support count sang **normalized support** (giá trị trong khoảng 0..1), rồi tính đủ 4 metric chuẩn.

Chi tiết thực hiện trong `generate_rules`:

- Bỏ qua \(k=1\) (không sinh được luật).
- Với từng itemset `itemset` và `support`:
  - bắt đầu với `H_curr = [[x] for x in itemset]` (các consequent 1 phần tử)
  - thử từng `h` trong `H_curr`:
    - `X = itemset - h`
    - `Y = h`
    - lấy `antecedent_support_count` từ `frequent_items[k-2][X]`
    - lấy `consequent_support_count` từ `frequent_items[len(Y)-1][Y]`
    - gọi `calculate_rule_metrics(...)` để tính `support`, `confidence`, `lift`, `conviction`
    - gọi `passes_rule_filters(metrics)` để kiểm tra rule có đồng thời thỏa:
      - `confidence > MIN_CONF`
      - `lift > MIN_LIFT`
      - `conviction > MIN_CONVICTION`
    - nếu không thỏa, loại `h`
  - sau đó tăng kích thước consequent bằng cách:
    - `H_next = apriori_gen(H_curr)`
    - lặp tương tự cho \(m = 1..k-2\) (tức consequent size tăng dần)

Đầu ra:

- `rules`: list các dict dạng:
  - `{'antecedent': X, 'consequent': Y, 'metrics': {...}}`

Trong đó `metrics` chứa:

- `support_count`: số lần xuất hiện của toàn bộ luật \(X \cup Y\)
- `support`: normalized support của luật
- `antecedent_support_count`, `consequent_support_count`
- `antecedent_support`, `consequent_support`
- `confidence`
- `lift`
- `conviction`

#### 4.6. Xuất kết quả có cấu trúc — `display_rules(rules, frequent_items, total_transactions, write=True)`

Trong `display_rules`:

- load `reverse_map.pkl` để đổi id → tên item
- sort rule theo thứ tự giảm dần của `confidence`, sau đó `lift`, sau đó `support`, để file output dễ đọc hơn
- chuyển rules thành `rule_records` và frequent itemsets thành `frequent_itemset_records`
- ghi:
  - `outputs/association_rules.txt`: mỗi dòng có đầy đủ antecedent, consequent, `rule_support_count`, `support`, `confidence`, `lift`, `conviction`
  - `outputs/frequent_itemsets.txt`: mỗi dòng có cả `support_count` và `support`
- export thêm dữ liệu có cấu trúc:
  - `outputs/structured/association_rules.csv`
  - `outputs/structured/association_rules.json`
  - `outputs/structured/frequent_itemsets.csv`
  - `outputs/structured/frequent_itemsets.json`
  - `outputs/structured/mining_results.json`
- đồng thời cũng `print(...)` luật ra console.

#### 4.7. Sinh biểu đồ trực quan — `generate_visualizations(...)`

Sau khi mining và export structured output xong, `arm.py` gọi `generate_visualizations(...)` từ `visualize.py`.

Pipeline visualization hoạt động như sau:

- lấy `rule_records` và `frequent_itemset_records`
- chọn top-N theo từng loại biểu đồ để tránh chart quá rối
- sinh 2 nhóm output:
  - `visualizations/static/*.png`
  - `visualizations/interactive/*.html`

Chi tiết 4 biểu đồ:

- **Bar chart**
  - input: top frequent itemsets theo `support_count`
  - ý nghĩa: nhìn nhanh itemset nào phổ biến nhất

- **Scatter plot**
  - input: top rules
  - trục mặc định:
    - `x = support`
    - `y = confidence`
  - kích thước marker phản ánh `lift`
  - màu phản ánh `conviction`
  - ý nghĩa: nhìn tổng quan chất lượng của các luật trong một hình duy nhất

- **Network graph**
  - node là item
  - cạnh có hướng từ antecedent item sang consequent item
  - trọng số cạnh dựa trên `lift`
  - ý nghĩa: nhìn rõ các cụm item có liên kết mạnh về mặt luật kết hợp

- **Heatmap**
  - tạo ma trận item × item từ các rule mạnh nhất
  - ô trong ma trận chứa giá trị `lift`
  - ý nghĩa: xem cặp antecedent/consequent nào mạnh nhất dưới dạng ma trận

Cuối cùng, `arm.py` in:

- số luật (`len(rules)`)
- tổng số itemset (cộng `len(dict)` của từng `Lk`)

### 5) Hash Tree được dùng để đếm support như thế nào?

Phần này nằm trong `hash_tree.py`.

#### 5.1. Cấu trúc dữ liệu

- `Node`: leaf node chứa `children` là dict:
  - key: `tuple(candidate)`
  - value: `count` (support count)
- `Tree`: internal node (hoặc root) chứa `children` là dict:
  - key: `hash_value = candidate[depth] % k`
  - value: một `Node` (leaf) hoặc một `Tree` (subtree) sau khi split

`Tree` có:

- `depth`: đang băm theo phần tử thứ `depth` của candidate
- `k`: mẫu số hash (ở `arm.py` truyền vào là `HASH_DENOMINATOR`)
- `max_leaf_size`: leaf chứa quá nhiều candidate thì split thành subtree
- `c_length`: độ dài candidate itemset (kích thước itemset đang đếm)

#### 5.2. Insert candidate vào tree — `Tree.build_tree(c_list)`

Với mỗi `candidate`:

- tính bucket: `candidate[self.depth] % self.k`
- nếu chưa có bucket thì tạo leaf `Node(...)`
- `Node.add(candidate)` thêm candidate vào leaf với count khởi tạo 0

Sau khi insert xong:

- `update_tree()` kiểm tra leaf nào vượt `max_leaf_size` thì split thành `Tree` ở `depth+1` (nếu chưa vượt quá `c_length`)

#### 5.3. Cập nhật/tra cứu support — `Tree.check(candidate, update=False)`

- đi theo bucket tương ứng với `candidate[depth] % k`
- nếu child là subtree (`isTree=True`) thì đệ quy xuống
- nếu child là leaf:
  - nếu candidate có trong leaf:
    - nếu `update=True` thì tăng count
    - trả về count
  - nếu không có thì trả 0

Trong `arm.py/subset(...)`, thay vì thử từng candidate trên từng transaction, code:

- sinh tất cả subset độ dài \(k\) của transaction
- với mỗi subset, gọi `check(update=True)` để tăng count đúng candidate tương ứng (nếu subset đó trùng candidate)

Điểm cốt lõi:

- Hash tree giúp **giảm không gian tìm kiếm** khi cập nhật count, vì mỗi subset chỉ đi theo 1 nhánh hash thay vì so khớp với toàn bộ candidate list.

#### 5.4. Sinh subset transaction — `generate_subsets(transaction, k)`

`generate_subsets` sinh tổ hợp \(k\) phần tử của transaction bằng đệ quy (tương tự combinations):

- sort transaction
- đệ quy chọn phần tử, đẩy vào `res`

Kết quả `res` là list các subset độ dài đúng `k` (mỗi subset là list int).

### 6) Giải thích rõ ý nghĩa 4 metric của association rule

- **Support**
  - Cho biết luật xuất hiện trong bao nhiêu phần trăm transaction.
  - Nếu support thấp, luật có thể đúng nhưng ít giá trị thực tiễn vì quá hiếm.

- **Confidence**
  - Cho biết khi có \(X\), xác suất thấy thêm \(Y\) là bao nhiêu.
  - Đây là metric đang được dùng để lọc rule trong code thông qua `MIN_CONF`.

- **Lift**
  - So sánh rule với trường hợp \(X\) và \(Y\) độc lập.
  - `lift > 1`: \(X\) và \(Y\) có xu hướng đi cùng nhau mạnh hơn ngẫu nhiên.
  - `lift = 1`: gần như độc lập.
  - `lift < 1`: xuất hiện cùng nhau kém hơn mong đợi.
  - Trong bản hiện tại, code yêu cầu `lift > 1.2`.

- **Conviction**
  - Đo mức độ “vi phạm kỳ vọng độc lập”.
  - Conviction càng lớn thì luật càng mạnh theo hướng có tính kéo theo.
  - Nếu `confidence = 1`, công thức chia cho 0; trong code, trường hợp này được biểu diễn là `inf`.
  - Trong bản hiện tại, code yêu cầu `conviction > 1.2`.

### 7) Vì sao 4 biểu đồ này hợp lý với bài toán

- **Bar chart cho frequent itemsets**
  - Hợp lý vì frequent itemsets vốn là dữ liệu dạng xếp hạng.
  - Người đọc cần biết itemset nào xuất hiện nhiều nhất, nên biểu đồ cột là trực quan nhất.

- **Scatter plot cho association rules**
  - Hợp lý vì mỗi rule có nhiều metric cùng lúc (`support`, `confidence`, `lift`, `conviction`).
  - Scatter plot cho phép đặt 2 metric lên trục, 1 metric vào màu, 1 metric vào kích thước điểm.
  - Đây là cách phù hợp để nhìn “toàn cảnh luật”.

- **Network graph cho quan hệ luật**
  - Hợp lý vì luật kết hợp về bản chất là mối liên hệ giữa các item.
  - Dạng mạng giúp nhìn ra cụm item trung tâm và các hướng liên kết mạnh.
  - Tuy nhiên chỉ nên dùng top rules, nếu không biểu đồ sẽ rất rối.

- **Heatmap cho ma trận chéo**
  - Hợp lý khi muốn so sánh nhanh nhiều cặp item với nhau.
  - Dùng `lift` trong heatmap sẽ giúp thấy cặp nào mạnh hơn rõ rệt.
  - Cũng cần top-N, vì ma trận quá lớn sẽ khó đọc.

### 8) Các “công nghệ”/thành phần Python được dùng trong dự án

- **Chuẩn thư viện (stdlib)**:
  - `csv`: đọc dữ liệu transactions từ file CSV.
  - `json`: ghi structured outputs để các công cụ khác có thể dùng lại dễ dàng.
  - `pickle`: lưu/đọc `reverse_map.pkl` và `l_final.pkl`.
  - `os`: có import và có đoạn comment về việc load `l_final.pkl`.
- **Decorator**:
  - `@timeit` trong `timing_wrapper.py` dùng để in thời gian chạy các hàm (vd `load_data`, `subset`).
- **Visualization stack**:
  - `matplotlib`: vẽ biểu đồ tĩnh dạng PNG.
  - `seaborn`: làm đẹp bar chart và heatmap.
  - `plotly`: tạo biểu đồ HTML tương tác có hover/zoom/pan.
  - `networkx`: xây dựng layout cho network graph.

### 9) Output cuối cùng gồm những gì?

Sau khi chạy xong `python arm.py`, bạn sẽ có:

- **Apriori**:
  - `outputs/apriori/frequent_itemsets.txt`
  - `outputs/apriori/association_rules.txt`
  - `outputs/apriori/structured/*.csv` và `outputs/apriori/structured/*.json`
  - `visualizations/apriori/static/*.png`
  - `visualizations/apriori/interactive/*.html`

Chạy `python fp_growth.py` sẽ sinh:

- **FP-Growth**:
  - `outputs/fp_growth/frequent_itemsets.txt`
  - `outputs/fp_growth/association_rules.txt`
  - `outputs/fp_growth/structured/*.csv` và `outputs/fp_growth/structured/*.json`
  - `visualizations/fp_growth/static/*.png`
  - `visualizations/fp_growth/interactive/*.html`

Chạy `python compare_algorithms.py` sẽ sinh:

- **Benchmark**:
  - `outputs/comparison/*`
  - `visualizations/benchmark_performance.png`
- `reverse_map.pkl`: mapping id → item
- `l_final.pkl`: cấu trúc `L_final` (list các dict support counts theo từng \(k\))

### 10) Gợi ý thay đổi cấu hình và chạy lại

Bạn chỉnh ở đầu `arm.py`:

- tăng/giảm `MINSUP` để ít/nhiều frequent itemsets hơn
- tăng/giảm `MIN_CONF` để luật “mạnh” hơn hoặc nhiều hơn
- tăng/giảm `MIN_LIFT` để kiểm soát mức độ phụ thuộc giữa antecedent và consequent
- tăng/giảm `MIN_CONVICTION` để kiểm soát độ mạnh của tính kéo theo
- thử các giá trị `HASH_DENOMINATOR` khác để so sánh tốc độ hash tree
- tăng/giảm các giá trị `TOP_N_*` để biểu đồ ít hoặc nhiều chi tiết hơn
- đặt `RUN_VISUALIZATIONS = False` nếu chỉ muốn mining mà không sinh chart

Sau đó chạy lại:

```bash
python arm.py
```

