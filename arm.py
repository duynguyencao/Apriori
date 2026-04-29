import csv
import json
import pickle
import os
from hash_tree import Tree, generate_subsets
from timing_wrapper import timeit
from visualize import generate_visualizations
import config

# Cấu hình đã được gom về `config.py` để Apriori/FP-Growth/Benchmark dùng chung.
MINSUP = config.MINSUP
HASH_DENOMINATOR = config.HASH_DENOMINATOR
MIN_CONF = config.MIN_CONF
MIN_LIFT = config.MIN_LIFT
MIN_CONVICTION = config.MIN_CONVICTION
RUN_VISUALIZATIONS = config.RUN_VISUALIZATIONS
TOP_N_ITEMSETS = config.TOP_N_ITEMSETS
TOP_N_RULES = config.TOP_N_RULES
TOP_N_NETWORK_RULES = config.TOP_N_NETWORK_RULES
TOP_N_HEATMAP_ITEMS = config.TOP_N_HEATMAP_ITEMS

DEFAULT_OUTPUT_DIR = config.APRIORI_OUTPUT_DIR
DEFAULT_VISUALIZATION_DIR = config.APRIORI_VIS_DIR

@timeit
def load_data(path):
	'''
	Đọc toàn bộ dữ liệu giao dịch từ file CSV.

	Đầu vào:
	- `path`: đường dẫn tới file dữ liệu.

	Đầu ra:
	- `transactions`: danh sách transaction, mỗi transaction là một list item.
	- `items`: danh sách item duy nhất trong toàn bộ dữ liệu.

	Lưu ý:
	- Hàm này chỉ đọc dữ liệu thô, chưa ánh xạ item sang số nguyên.
	- Việc chuẩn hóa item diễn ra ở bước sau để tối ưu cho Apriori và hash tree.
	'''
	items = []
	with open(path, 'r') as f:
		reader = csv.reader(f)
		transactions = list(reader)
	for x in transactions:
		items.extend(x)
	items=sorted(set(items))
	return transactions, items

def create_map(items):
	'''
	Tạo ánh xạ hai chiều giữa tên item và số nguyên.

	Mục đích:
	- Giảm chi phí lưu trữ và so sánh khi chạy Apriori.
	- Dễ chuẩn hóa candidate itemset theo thứ tự số.
	- Vẫn giữ được khả năng đổi ngược sang tên item khi xuất kết quả.
	'''
	map_ = {x:i for i,x in enumerate(items)}
	reverse_map = {i:x for i,x in enumerate(items)}
	return map_, reverse_map

def applymap(transaction, map_):
	'''
	Áp dụng ánh xạ item -> số nguyên cho một transaction hoặc itemset.

	Lưu ý:
	- Hàm này không sắp xếp lại transaction.
	- Việc chuẩn hóa thứ tự được xử lý ở những bước cần thiết như sinh subset hoặc sinh candidate.
	'''
	ret = []
	for item in transaction:
		ret.append(map_[item])
	return ret

def support_from_count(count, total_transactions):
	'''
	Chuyển support count sang support chuẩn hóa trong khoảng [0, 1].
	'''
	return count / total_transactions

def format_itemset(itemset, reverse_map):
	'''
	Đổi itemset ở dạng số nguyên sang chuỗi dễ đọc để ghi file hoặc hiển thị.
	'''
	return ', '.join([reverse_map[x] for x in itemset])

def ensure_directory(path):
	'''
	Tạo thư mục nếu chưa tồn tại.
	'''
	os.makedirs(path, exist_ok=True)

def calculate_rule_metrics(itemset_support_count, antecedent_support_count, consequent_support_count, total_transactions):
	'''
	Tính đầy đủ các metric của một luật: support, confidence, lift, conviction.

	Tham số đầu vào đều là support count để tận dụng kết quả Apriori đã tính sẵn.
	Sau đó hàm mới quy đổi về support chuẩn hóa khi cần.

	Lưu ý:
	- Nếu confidence = 1 thì conviction là vô cùng (`inf`).
	- Trường hợp này là hợp lệ về mặt toán học, không phải lỗi tính toán.
	'''
	support_itemset = support_from_count(itemset_support_count, total_transactions)
	support_antecedent = support_from_count(antecedent_support_count, total_transactions)
	support_consequent = support_from_count(consequent_support_count, total_transactions)
	confidence = itemset_support_count / antecedent_support_count
	lift = confidence / support_consequent
	if confidence == 1:
		conviction = float('inf')
	else:
		conviction = (1 - support_consequent) / (1 - confidence)
	return {
		'support_count': itemset_support_count,
		'support': support_itemset,
		'antecedent_support_count': antecedent_support_count,
		'antecedent_support': support_antecedent,
		'consequent_support_count': consequent_support_count,
		'consequent_support': support_consequent,
		'confidence': confidence,
		'lift': lift,
		'conviction': conviction
	}

def format_metric(value):
	'''
	Định dạng metric số thực để file output gọn và dễ đọc hơn.
	'''
	if value == float('inf'):
		return 'inf'
	return f'{value:.6f}'

def passes_rule_filters(metrics):
	'''
	Kiểm tra một rule có vượt toàn bộ ngưỡng lọc đã cấu hình hay không.

	Rule chỉ được giữ lại khi đồng thời thỏa:
	- confidence > MIN_CONF
	- lift > MIN_LIFT
	- conviction > MIN_CONVICTION
	'''
	return (
		metrics['confidence'] > MIN_CONF and
		metrics['lift'] > MIN_LIFT and
		metrics['conviction'] > MIN_CONVICTION
	)

def build_rule_record(rule, reverse_map):
	'''
	Chuẩn hóa một rule nội bộ thành record có cấu trúc.

	Record này được dùng cho 3 mục đích:
	- ghi JSON/CSV
	- dựng visualization
	- tránh phải parse ngược từ file text về sau
	'''
	antecedent = rule['antecedent']
	consequent = rule['consequent']
	metrics = rule['metrics']
	return {
		'antecedent_ids': list(antecedent),
		'antecedent_items': [reverse_map[x] for x in antecedent],
		'antecedent_label': format_itemset(antecedent, reverse_map),
		'consequent_ids': list(consequent),
		'consequent_items': [reverse_map[y] for y in consequent],
		'consequent_label': format_itemset(consequent, reverse_map),
		'rule_size': len(antecedent) + len(consequent),
		'antecedent_size': len(antecedent),
		'consequent_size': len(consequent),
		'rule_support_count': metrics['support_count'],
		'rule_support': metrics['support'],
		'antecedent_support_count': metrics['antecedent_support_count'],
		'antecedent_support': metrics['antecedent_support'],
		'consequent_support_count': metrics['consequent_support_count'],
		'consequent_support': metrics['consequent_support'],
		'confidence': metrics['confidence'],
		'lift': metrics['lift'],
		'conviction': metrics['conviction']
	}

def build_frequent_itemset_record(itemset, support_count, reverse_map, total_transactions):
	'''
	Chuẩn hóa một frequent itemset thành record có cấu trúc.
	'''
	return {
		'itemset_ids': list(itemset),
		'itemset_items': [reverse_map[x] for x in itemset],
		'itemset_label': format_itemset(itemset, reverse_map),
		'itemset_size': len(itemset),
		'support_count': support_count,
		'support': support_from_count(support_count, total_transactions)
	}

def export_structured_outputs(rule_records, frequent_itemset_records, output_dir):
	'''
	Ghi structured outputs ra JSON và CSV.

	Đây là bước rất quan trọng nếu muốn:
	- trực quan hóa dữ liệu mà không phụ thuộc vào text thuần
	- đưa dữ liệu sang các công cụ khác như Excel, Pandas, BI tools
	- tái sử dụng output cho các lần phân tích sau
	'''
	ensure_directory(output_dir)
	json_payload = {
		'association_rules': rule_records,
		'frequent_itemsets': frequent_itemset_records
	}
	with open(os.path.join(output_dir, 'association_rules.json'), 'w+', encoding='utf-8') as f:
		json.dump(rule_records, f, ensure_ascii=False, indent=2)
	with open(os.path.join(output_dir, 'frequent_itemsets.json'), 'w+', encoding='utf-8') as f:
		json.dump(frequent_itemset_records, f, ensure_ascii=False, indent=2)
	with open(os.path.join(output_dir, 'mining_results.json'), 'w+', encoding='utf-8') as f:
		json.dump(json_payload, f, ensure_ascii=False, indent=2)

	with open(os.path.join(output_dir, 'association_rules.csv'), 'w+', newline='', encoding='utf-8') as f:
		fieldnames = [
			'antecedent_label', 'consequent_label', 'antecedent_size', 'consequent_size',
			'rule_size', 'rule_support_count', 'rule_support', 'antecedent_support_count',
			'antecedent_support', 'consequent_support_count', 'consequent_support',
			'confidence', 'lift', 'conviction'
		]
		writer = csv.DictWriter(f, fieldnames=fieldnames)
		writer.writeheader()
		for record in rule_records:
			writer.writerow({key: record[key] for key in fieldnames})

	with open(os.path.join(output_dir, 'frequent_itemsets.csv'), 'w+', newline='', encoding='utf-8') as f:
		fieldnames = ['itemset_label', 'itemset_size', 'support_count', 'support']
		writer = csv.DictWriter(f, fieldnames=fieldnames)
		writer.writeheader()
		for record in frequent_itemset_records:
			writer.writerow({key: record[key] for key in fieldnames})

def apriori_gen(l_prev):
	'''
	Sinh candidate `C(k+1)` từ tập frequent itemsets `L(k)`.

	Cách làm:
	- Duyệt từng cặp itemset trong `l_prev`.
	- Nếu hai itemset có cùng tiền tố độ dài `k-1`, ta join chúng lại.
	- Kết quả được sort để giữ biểu diễn thống nhất.

	Lưu ý:
	- Đây là join step của Apriori.
	- Bản cài hiện tại không tách riêng prune step cổ điển; việc loại candidate yếu
	  được thực hiện ở vòng đếm support và lọc theo `MINSUP`.
	'''
	n = len(l_prev)
	c_curr = []
	for i in range(n):
		for j in range(i+1, n):
			temp_a = l_prev[i]
			temp_b = l_prev[j]
			if temp_a[:-1] == temp_b[:-1]:
				# Chỉ khi tiền tố giống nhau mới được phép join theo nguyên lý Apriori.
				temp_c = []
				temp_c.extend(temp_a)
				temp_c.append(temp_b[-1])
				temp_c=sorted(temp_c)
				c_curr.append(temp_c)
	return c_curr

# Bản brute force được giữ lại để tham khảo hoặc so sánh hiệu năng.
# @timeit
# def subset(c_list, transactions):
# 	candidate_counts={}
# 	for transaction in transactions:
# 		for candidate in c_list:
# 			if set(candidate).issubset(set(transaction)):
# 				candidate_counts[tuple(candidate)] = candidate_counts.get(tuple(candidate), 0)
# 				candidate_counts[tuple(candidate)] += 1
# 	return candidate_counts

@timeit
def subset(c_list, transactions):
	'''
	Đếm support count cho toàn bộ candidate trong `c_list` bằng hash tree.

	Cách làm:
	1. Xây hash tree từ danh sách candidate.
	2. Với mỗi transaction, sinh toàn bộ subset có cùng kích thước với candidate.
	3. Dùng hash tree để cập nhật support count cho đúng candidate tương ứng.

	Lưu ý:
	- Đây là phần tối ưu quan trọng nhất của dự án.
	- Nếu `c_list` quá lớn, tốc độ vẫn phụ thuộc mạnh vào số subset sinh ra từ transaction.
	'''
	candidate_counts={}
	t=Tree(c_list, k=HASH_DENOMINATOR, max_leaf_size=100)
	for transaction in transactions:
		subsets =generate_subsets(transaction, len(c_list[0]))
		for sub in subsets:
			t.check(sub, update=True)
	for candidate in c_list:
		candidate_counts[tuple(candidate)] = t.check(candidate, update=False)
	return candidate_counts

def frequent_itemset_generation(data_path):
	'''
	Đọc dữ liệu và sinh toàn bộ frequent itemsets bằng thuật toán Apriori.

	Đầu ra:
	- `L_final`: list các dictionary `L1, L2, ..., Lk`
	- `total_transactions`: tổng số transaction

	Lưu ý:
	- Mỗi `Lk` là một dict: key là tuple itemset, value là support count.
	- Hàm này chỉ làm phần frequent itemset mining, chưa sinh luật.
	'''

	# Có thể bỏ comment đoạn dưới nếu muốn tái sử dụng kết quả frequent itemset đã lưu.
	# Cách này giúp tiết kiệm thời gian khi chỉ muốn thử phần sinh luật hoặc visualization.
	# if 'l_final.pkl' in os.listdir('.'):
	# 	return pickle.load(open('l_final.pkl', 'rb'))
	transactions, items = load_data(data_path)
	total_transactions = len(transactions)
	map_, reverse_map = create_map(items)
	pickle.dump(reverse_map, open('reverse_map.pkl', 'wb+'))
	one_itemset = [[itemset] for itemset in items]
	items_mapped = [applymap(itemset, map_) for itemset in one_itemset]
	transactions_mapped = [applymap(transaction, map_) for transaction in transactions]
	
	temp_l_current = subset(items_mapped, transactions_mapped)
	l_current={}
	for t in temp_l_current.keys():
		if temp_l_current[t] > MINSUP:
			l_current[tuple(t)] = temp_l_current[t]
	L_final = []
	L_final.append(l_current)

	while(len(l_current)):
		# Từ L(k) sinh C(k+1), rồi đếm support để lấy lại L(k+1).
		c_current = apriori_gen(list(l_current.keys()))
		if len(c_current):
			C_t = subset(c_current, transactions_mapped)
			l_current = {}
			for c in C_t.keys():
				if C_t[c] > MINSUP:
					l_current[tuple(sorted(c))] = C_t[c]
			if len(l_current):
				L_final.append(l_current)
		else:
			break
	pickle.dump(L_final, open('l_final.pkl', 'wb+'))
	return L_final, total_transactions

def generate_rules(frequent_items, total_transactions):
	'''
	Sinh association rules từ tập frequent itemsets.

	Biểu diễn đầu ra:
	[
		{
			'antecedent': X,
			'consequent': Y,
			'metrics': {...}
		},
		...
	]

	Lưu ý:
	- Hàm này chỉ sinh rule từ các itemset đã vượt `MINSUP`.
	- Sau khi tính metric, rule còn phải vượt các ngưỡng lọc `MIN_CONF`, `MIN_LIFT`, `MIN_CONVICTION`.
	'''
	rules=[]
	for k_itemset in frequent_items:
		k=len(list(k_itemset.keys())[0])
		if k==1: # Tập 1 phần tử không thể tách thành antecedent và consequent hợp lệ.
			continue
		for itemset, support in k_itemset.items():
			# H_curr chứa các consequent ứng viên ở kích thước hiện tại.
			H_curr=[[x] for x in itemset]
			to_remove=[]
			for h in H_curr:
				X=tuple(sorted(set(itemset)-set(h)))
				Y=tuple(sorted(h))
				antecedent_support_count = frequent_items[k-2][X]
				consequent_support_count = frequent_items[len(Y)-1][Y]
				metrics = calculate_rule_metrics(support, antecedent_support_count, consequent_support_count, total_transactions)
				if passes_rule_filters(metrics):
					rules.append({
						'antecedent': X,
						'consequent': Y,
						'metrics': metrics
					})
				else:
					to_remove.append(h)

			# Chỉ giữ lại các consequent đã vượt ngưỡng để sinh tiếp consequent lớn hơn.
			H_curr=[x for x in H_curr if x not in to_remove]

			for m in range(1,k-1):
				if k > m+1:
					H_next=apriori_gen(H_curr)
					to_remove=[]
					for h in H_next:
						X=tuple(sorted(set(itemset)-set(h)))
						Y=tuple(sorted(h))
						antecedent_support_count = frequent_items[k-m-2][X]
						consequent_support_count = frequent_items[len(Y)-1][Y]
						metrics = calculate_rule_metrics(support, antecedent_support_count, consequent_support_count, total_transactions)
						if passes_rule_filters(metrics):
							rules.append({
								'antecedent': X,
								'consequent': Y,
								'metrics': metrics
							})
						else:
							to_remove.append(h)
					H_next=[x for x in H_next if x not in to_remove]
					H_curr=H_next
				else:
					break	
	return rules

def display_rules(rules, frequent_items, total_transactions, output_dir, write=False):
	'''
	Hiển thị và ghi kết quả ra file text, đồng thời export structured output.

	Ngoài hai file text truyền thống, hàm này còn:
	- chuẩn hóa dữ liệu rule/itemset thành records
	- ghi JSON/CSV vào `outputs/structured`
	- trả lại records để module visualization dùng trực tiếp
	'''
	reverse_map=pickle.load(open('reverse_map.pkl', 'rb'))
	ensure_directory(output_dir)
	structured_dir = os.path.join(output_dir, 'structured')
	ensure_directory(structured_dir)
	# Sắp xếp rule để file output ưu tiên các luật mạnh và đáng chú ý nhất ở trên đầu.
	sorted_rules = sorted(
		rules,
		key=lambda rule: (
			rule['metrics']['confidence'],
			rule['metrics']['lift'],
			rule['metrics']['support']
		),
		reverse=True
	)
	rule_records = [build_rule_record(rule, reverse_map) for rule in sorted_rules]
	frequent_itemset_records = []
	for k_itemset in frequent_items:
		for itemset, support in k_itemset.items():
			frequent_itemset_records.append(
				build_frequent_itemset_record(itemset, support, reverse_map, total_transactions)
			)
	frequent_itemset_records = sorted(
		frequent_itemset_records,
		key=lambda itemset: (itemset['support_count'], itemset['itemset_size']),
		reverse=True
	)
	with open(os.path.join(output_dir, 'association_rules.txt'), 'w+', encoding='utf-8') as f:
		for record in rule_records:
			line = (
				f'{record["antecedent_label"]} '
				f'(support_count={record["antecedent_support_count"]})'
				f' ---> '
				f'{record["consequent_label"]} '
				f'(support_count={record["consequent_support_count"]})'
				f' | rule_support_count={record["rule_support_count"]}'
				f' | support={format_metric(record["rule_support"])}'
				f' | confidence={format_metric(record["confidence"])}'
				f' | lift={format_metric(record["lift"])}'
				f' | conviction={format_metric(record["conviction"])}'
			)
			print(line)
			f.write(line + '\n')

	with open(os.path.join(output_dir, 'frequent_itemsets.txt'), 'w+', encoding='utf-8') as f:
		for record in frequent_itemset_records:
			f.write(
				f'{record["itemset_label"]} '
				f'(support_count={record["support_count"]}, support={format_metric(record["support"])})\n'
			)

	export_structured_outputs(rule_records, frequent_itemset_records, structured_dir)
	return rule_records, frequent_itemset_records
			
if __name__=='__main__':
	# Luồng chính:
	# 1. Đọc dữ liệu và sinh frequent itemsets
	# 2. Sinh rules và tính metric
	# 3. Ghi output text + structured output
	# 4. Nếu bật cờ, sinh thêm visualization
	data_path = config.DATA_PATH
	frequent_items, total_transactions = frequent_itemset_generation(data_path)
	rules = generate_rules(frequent_items, total_transactions)
	rule_records, frequent_itemset_records = display_rules(
		rules,
		frequent_items,
		total_transactions,
		output_dir=DEFAULT_OUTPUT_DIR,
		write=True,
	)
	if RUN_VISUALIZATIONS:
		generate_visualizations(
			rule_records,
			frequent_itemset_records,
			output_dir=DEFAULT_VISUALIZATION_DIR,
			top_n_itemsets=TOP_N_ITEMSETS,
			top_n_rules=TOP_N_RULES,
			top_n_network_rules=TOP_N_NETWORK_RULES,
			top_n_heatmap_items=TOP_N_HEATMAP_ITEMS
		)
	no_itemsets=0
	for x in frequent_items:
		no_itemsets+=len(x)
	print('No of rules:',len(rules), 'No of itemsets:', no_itemsets)