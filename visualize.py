import math
import os
import importlib

def _optional_import(module_name):
	try:
		return importlib.import_module(module_name)
	except ModuleNotFoundError:
		return None


matplotlib = _optional_import('matplotlib')
if matplotlib is not None:
	matplotlib.use('Agg')
	plt = _optional_import('matplotlib.pyplot')
else:
	plt = None

nx = _optional_import('networkx')
sns = _optional_import('seaborn')
go_module = _optional_import('plotly.graph_objects')
go = go_module

VISUALIZATION_BACKEND_AVAILABLE = all(
	backend is not None
	for backend in (plt, nx, sns, go)
)


def ensure_directory(path):
	'''
	Tạo thư mục nếu chưa tồn tại.

	Hàm này được gọi lặp lại ở nhiều nơi vì pipeline visualization sinh ra
	nhiều nhóm file khác nhau (`static`, `interactive`).
	'''
	os.makedirs(path, exist_ok=True)


def write_placeholder_html(output_path, title, message):
	'''
	Ghi file HTML thay thế khi môi trường chưa cài Plotly.

	Mục tiêu là giữ pipeline không bị gãy ở bước xuất HTML tương tác.
	'''
	with open(output_path, 'w', encoding='utf-8') as handle:
		handle.write(
			'<!DOCTYPE html>\n'
			'<html lang="vi">\n'
			'<head>\n'
			'  <meta charset="utf-8">\n'
			f'  <title>{title}</title>\n'
			'  <style>body{font-family:Arial,sans-serif;margin:40px;line-height:1.6}code{background:#f4f4f4;padding:2px 4px;border-radius:4px}</style>\n'
			'</head>\n'
			'<body>\n'
			f'  <h1>{title}</h1>\n'
			f'  <p>{message}</p>\n'
			'</body>\n'
			'</html>\n'
		)

def setup_matplotlib_font():
	'''
	Cấu hình font mặc định để Matplotlib hiển thị tiếng Việt tốt hơn.

	Lưu ý:
	- Một số môi trường có thể thiếu font đầy đủ glyph tiếng Việt.
	- `DejaVu Sans` thường có sẵn và hỗ trợ khá tốt.
	'''
	if plt is None:
		return
	plt.rcParams['font.family'] = 'DejaVu Sans'
	plt.rcParams['axes.unicode_minus'] = False
	# Theme doanh nghiệp cho ảnh tĩnh: nền lưới xám nhạt, màu dịu (chuẩn báo cáo).
	sns.set_theme(style="whitegrid", palette="muted")


def truncate_label(label, max_length=40):
	'''
	Cắt ngắn nhãn quá dài để biểu đồ không bị chồng chữ.

	Lưu ý:
	- Chỉ dùng cho phần hiển thị.
	- Dữ liệu gốc trong JSON/CSV vẫn giữ đầy đủ để tra cứu hoặc dùng hover.
	'''
	if len(label) <= max_length:
		return label
	return label[: max_length - 3] + '...'


def top_records(records, sort_keys, limit):
	'''
	Lấy top-N record theo danh sách khóa sắp xếp.

	Cách làm này giúp cùng một nguồn dữ liệu có thể tái sử dụng cho nhiều loại biểu đồ,
	chỉ khác nhau ở tiêu chí chọn bản ghi nổi bật nhất.
	'''
	return sorted(
		records,
		key=lambda record: tuple(record[key] for key in sort_keys),
		reverse=True
	)[:limit]


def normalize_sizes(values, minimum=10, maximum=35):
	'''
	Chuẩn hóa danh sách số về một khoảng kích thước trực quan.

	Dùng trong scatter plot hoặc network graph để biến metric như `lift`
	thành kích thước marker/độ dày cạnh.
	'''
	if not values:
		return []
	low = min(values)
	high = max(values)
	if math.isclose(low, high):
		# Nếu mọi giá trị gần như bằng nhau, dùng một kích thước trung bình
		# để tránh chia cho 0 và tránh hiểu nhầm là có khác biệt lớn.
		return [minimum + (maximum - minimum) / 2 for _ in values]
	return [
		minimum + (value - low) * (maximum - minimum) / (high - low)
		for value in values
	]

def safe_float(value):
	'''
	Plotly/JSON có thể gặp `inf`. Hàm này chuyển `inf`/`nan` về None để tránh lỗi hiển thị.
	'''
	if value is None:
		return None
	if isinstance(value, float) and (math.isinf(value) or math.isnan(value)):
		return None
	return float(value)

def compute_rule_score(rule_record):
	'''
	Điểm tổng hợp để chọn “luật vàng”.

	Nguyên tắc:
	- Ưu tiên luật vừa “đúng” (confidence cao), vừa “có giá trị” (lift/conviction cao),
	  đồng thời không quá hiếm (support đủ lớn).
	'''
	conv = rule_record.get('conviction')
	conv_value = 1e9 if conv == float('inf') else (safe_float(conv) or 0.0)
	return (rule_record['confidence'], rule_record['rule_support'], rule_record['lift'], conv_value)

def export_golden_rules(rule_records, output_dir, top_n=10):
	'''
	Đóng gói Top luật vàng (5–10 luật) ra file riêng để dùng cho phần kết luận/đề xuất.
	'''
	import json
	ensure_directory(output_dir)
	golden = sorted(rule_records, key=compute_rule_score, reverse=True)[:top_n]
	with open(os.path.join(output_dir, 'golden_rules.txt'), 'w', encoding='utf-8') as f:
		for idx, rule in enumerate(golden, start=1):
			f.write(
				f'{idx}. {rule["antecedent_label"]} -> {rule["consequent_label"]} | '
				f'support={rule["rule_support"]:.6f} | '
				f'conf={rule["confidence"]:.6f} | '
				f'lift={rule["lift"]:.6f} | '
				f'conviction={rule["conviction"]}\n'
			)
	with open(os.path.join(output_dir, 'golden_rules.json'), 'w', encoding='utf-8') as f:
		json.dump(golden, f, ensure_ascii=False, indent=2)
	return golden


def save_bar_chart_png(itemsets, output_path):
	'''
	Vẽ bar chart tĩnh cho top frequent itemsets.
	'''
	setup_matplotlib_font()
	labels = [truncate_label(record['itemset_label']) for record in itemsets]
	values = [record['support_count'] for record in itemsets]
	plt.figure(figsize=(14, 8))
	sns.barplot(x=values, y=labels, hue=labels, palette='Blues_d', legend=False)
	plt.title('Top nhóm sản phẩm thường được mua cùng nhau (Frequent Itemsets)')
	plt.xlabel('Số lần xuất hiện (Support Count)')
	plt.ylabel('Nhóm sản phẩm')
	plt.tight_layout()
	plt.savefig(output_path, dpi=200, facecolor='white')
	plt.close()


def save_bar_chart_html(itemsets, output_path):
	'''
	Vẽ bar chart tương tác bằng Plotly.

	Phù hợp khi người dùng muốn hover để đọc đầy đủ itemset dài.
	'''
	if go is None:
		write_placeholder_html(
			output_path,
			'Top nhóm sản phẩm thường được mua cùng nhau',
			'Plotly chưa được cài trong môi trường hiện tại nên HTML tương tác này được thay bằng trang mô tả.'
		)
		return

	labels = [record['itemset_label'] for record in itemsets]
	values = [record['support_count'] for record in itemsets]
	supports = [record.get('support', None) for record in itemsets]
	fig = go.Figure(
		go.Bar(
			x=values,
			y=labels,
			orientation='h',
			customdata=supports,
			hovertemplate='Nhóm sản phẩm: %{y}<br>Support count: %{x}<br>Support: %{customdata:.6f}<extra></extra>'
		)
	)
	fig.update_layout(
		title='Top nhóm sản phẩm thường được mua cùng nhau (Frequent Itemsets)',
		xaxis_title='Số lần xuất hiện (Support Count)',
		yaxis_title='Nhóm sản phẩm',
		yaxis={'categoryorder': 'total ascending'},
		template='plotly_white'
	)
	fig.write_html(output_path)


def save_scatter_png(rules, output_path):
	'''
	Vẽ scatter plot tĩnh cho các luật.

	Quy ước trực quan:
	- trục x: support
	- trục y: confidence
	- kích thước điểm: lift
	- màu điểm: conviction
	'''
	setup_matplotlib_font()
	x = [record['rule_support'] for record in rules]
	y = [record['confidence'] for record in rules]
	sizes = normalize_sizes([record['lift'] for record in rules], minimum=40, maximum=220)
	colors = [safe_float(record.get('conviction')) for record in rules]
	plt.figure(figsize=(12, 8))
	plt.scatter(x, y, s=sizes, c=colors, cmap='viridis', alpha=0.75, edgecolors='black', linewidths=0.4)
	colorbar = plt.colorbar()
	colorbar.set_label('Conviction')
	plt.suptitle('Bản đồ chất lượng luật kết hợp', fontsize=14, fontweight='bold')
	plt.title('Góc trên cùng bên phải tập trung các luật có tính nhân quả mạnh nhất', fontsize=10, fontstyle='italic')
	plt.xlabel('Support')
	plt.ylabel('Confidence')
	plt.tight_layout()
	plt.savefig(output_path, dpi=200, facecolor='white')
	plt.close()


def save_scatter_html(rules, output_path):
	'''
	Vẽ scatter plot tương tác cho association rules.

	Điểm mạnh của bản HTML:
	- hover được tên luật đầy đủ
	- nhìn đồng thời 4 metric trên một biểu đồ
	'''
	if go is None:
		write_placeholder_html(
			output_path,
			'Bản đồ chất lượng luật kết hợp',
			'Plotly chưa được cài trong môi trường hiện tại nên HTML tương tác này được thay bằng trang mô tả.'
		)
		return

	fig = go.Figure(
		go.Scatter(
			x=[record['rule_support'] for record in rules],
			y=[record['confidence'] for record in rules],
			mode='markers',
			marker={
				'size': normalize_sizes([record['lift'] for record in rules], minimum=12, maximum=34),
				'color': [safe_float(record.get('conviction')) for record in rules],
				'colorscale': 'Viridis',
				'showscale': True,
				'colorbar': {'title': 'Conviction'},
				'line': {'width': 1, 'color': '#1f1f1f'}
			},
			text=[
				f'{record["antecedent_label"]} -> {record["consequent_label"]}'
				for record in rules
			],
			customdata=[
				[record['lift'], safe_float(record.get('conviction')), record['rule_support'], record['confidence']]
				for record in rules
			],
			hovertemplate=(
				'Luật: %{text}<br>'
				'Support: %{customdata[2]:.6f}<br>'
				'Confidence: %{customdata[3]:.6f}<br>'
				'Lift: %{customdata[0]:.6f}<br>'
				'Conviction: %{customdata[1]:.6f}<extra></extra>'
			)
		)
	)
	fig.update_layout(
		title={'text': "Bản đồ chất lượng luật kết hợp (Support vs Confidence)<br><sup><i>Giải thích: Các chấm to (Lift cao) và màu sáng (Conviction cao) ở góc trên bên phải là những luật mạnh nhất.</i></sup>"},
		xaxis_title='Support',
		yaxis_title='Confidence',
		template='plotly_white'
	)
	fig.write_html(output_path)

def save_scatter_golden_html(all_rules, golden_rules, output_path):
	'''
	Tạo một scatter plot riêng để highlight “luật vàng” phục vụ thuyết trình/demo.
	'''
	if go is None:
		write_placeholder_html(
			output_path,
			'Luật vàng nổi bật',
			'Plotly chưa được cài trong môi trường hiện tại nên HTML tương tác này được thay bằng trang mô tả.'
		)
		return

	def scatter_trace(rules, name, color):
		return go.Scatter(
			x=[record['rule_support'] for record in rules],
			y=[record['confidence'] for record in rules],
			mode='markers',
			name=name,
			marker={
				'size': normalize_sizes([record['lift'] for record in rules], minimum=10, maximum=28),
				'color': color,
				'line': {'width': 1, 'color': '#1f1f1f'},
				'opacity': 0.75
			},
			text=[f'{r["antecedent_label"]} -> {r["consequent_label"]}' for r in rules],
			customdata=[[r['lift'], safe_float(r.get('conviction'))] for r in rules],
			hovertemplate=(
				'Luật: %{text}<br>'
				'Support: %{x:.6f}<br>'
				'Confidence: %{y:.6f}<br>'
				'Lift: %{customdata[0]:.6f}<br>'
				'Conviction: %{customdata[1]:.6f}<extra></extra>'
			)
		)

	fig = go.Figure()
	fig.add_trace(scatter_trace(all_rules, 'Toàn bộ luật', '#90a4ae'))
	fig.add_trace(scatter_trace(golden_rules, 'Luật vàng (Top)', '#e63946'))
	fig.update_layout(
		title={'text': "Luật vàng nổi bật (Top 10 đề xuất chiến lược)<br><sup><i>Giải thích: Các chấm màu đỏ là những quy luật xuất sắc nhất đã được hệ thống tự động chắt lọc để lên campain Marketing.</i></sup>"},
		xaxis_title='Support',
		yaxis_title='Confidence',
		template='plotly_white'
	)
	fig.write_html(output_path)


def build_rule_graph(rules):
	'''
	Xây dựng đồ thị có hướng từ tập luật.

	Cách ánh xạ:
	- node: item
	- cạnh có hướng: antecedent item -> consequent item
	- trọng số cạnh: `lift`

	Lưu ý:
	- Với rule nhiều item ở hai vế, hàm này bung ra thành nhiều cạnh item-item.
	- Đây là cách trực quan hóa hợp lý hơn cho network graph so với giữ nguyên cả itemset làm một nút.
	'''
	graph = nx.DiGraph()
	for record in rules:
		for antecedent in record['antecedent_items']:
			graph.add_node(antecedent)
			for consequent in record['consequent_items']:
				graph.add_node(consequent)
				graph.add_edge(
					antecedent,
					consequent,
					lift=record['lift'],
					confidence=record['confidence'],
					support=record['rule_support'],
					conviction=safe_float(record.get('conviction'))
				)
	return graph


def save_network_png(rules, output_path):
	'''
	Vẽ network graph tĩnh.

	Sử dụng spring layout để các nút có xu hướng tách ra tự nhiên, giúp nhìn cụm liên kết rõ hơn.
	'''
	setup_matplotlib_font()
	graph = build_rule_graph(rules)
	plt.figure(figsize=(14, 10))
	# Tăng k để giãn node nhiều hơn, giảm chồng chữ khi số node tăng.
	positions = nx.spring_layout(graph, seed=42, k=1.6)
	# UI: độ dày cạnh theo Confidence, màu theo Lift.
	edge_confidences = [graph[u][v]['confidence'] for u, v in graph.edges()]
	edge_lifts = [graph[u][v]['lift'] for u, v in graph.edges()]
	widths = normalize_sizes(edge_confidences, minimum=1.0, maximum=5.0)
	nx.draw_networkx_nodes(graph, positions, node_size=1200, node_color='#8ecae6')
	nx.draw_networkx_labels(graph, positions, font_size=7)
	nx.draw_networkx_edges(
		graph,
		positions,
		width=widths,
		arrowstyle='->',
		arrowsize=18,
		edge_color=edge_lifts,
		edge_cmap=plt.cm.plasma,
		alpha=0.75
	)
	plt.suptitle('Bản đồ luồng hành vi mua sắm của khách hàng', fontsize=14, fontweight='bold')
	plt.title('Mũi tên thể hiện hướng mua kèm; cạnh dày hơn nghĩa là Confidence cao', fontsize=10, fontstyle='italic')
	plt.axis('off')
	plt.tight_layout()
	plt.savefig(output_path, dpi=200, facecolor='white')
	plt.close()


def save_network_html(rules, output_path):
	if go is None:
		write_placeholder_html(
			output_path,
			'Bản đồ luồng hành vi mua sắm của khách hàng',
			'Plotly chưa được cài trong môi trường hiện tại nên HTML tương tác này được thay bằng trang mô tả.'
		)
		return

	'''
	Vẽ network graph tương tác bằng Plotly.

	Bản HTML hữu ích hơn bản PNG khi số nút bắt đầu tăng, vì người dùng có thể
	hover để đọc tên item và bậc của nút.
	'''
	graph = build_rule_graph(rules)
	positions = nx.spring_layout(graph, seed=42, k=1.6)
	edge_x = []
	edge_y = []
	edge_hover_x = []
	edge_hover_y = []
	edge_hover_text = []
	edge_customdata = []
	for source, target in graph.edges():
		x0, y0 = positions[source]
		x1, y1 = positions[target]
		edge_x.extend([x0, x1, None])
		edge_y.extend([y0, y1, None])
		mx, my = (x0 + x1) / 2, (y0 + y1) / 2
		edge_hover_x.append(mx)
		edge_hover_y.append(my)
		data = graph[source][target]
		edge_hover_text.append(f'{source} -> {target}')
		edge_customdata.append([
			data.get('support', 0.0),
			data.get('confidence', 0.0),
			data.get('lift', 0.0),
			data.get('conviction', None)
		])

	edge_trace = go.Scatter(
		x=edge_x,
		y=edge_y,
		line={'width': 1, 'color': '#7f8c8d'},
		hoverinfo='none',
		mode='lines'
	)

	# Hack để có tooltip cho cạnh: đặt marker ở midpoint mỗi cạnh.
	edge_hover_trace = go.Scatter(
		x=edge_hover_x,
		y=edge_hover_y,
		mode='markers',
		marker={
			'size': normalize_sizes([x[1] for x in edge_customdata], minimum=6, maximum=14),
			'color': [x[2] for x in edge_customdata],
			'colorscale': 'Plasma',
			'showscale': True,
			'colorbar': {'title': 'Lift'},
			'line': {'width': 1, 'color': '#023047'},
			'opacity': 0.9
		},
		text=edge_hover_text,
		customdata=edge_customdata,
		hovertemplate=(
			'Luồng: %{text}<br>'
			'Support: %{customdata[0]:.6f}<br>'
			'Confidence: %{customdata[1]:.6f}<br>'
			'Lift: %{customdata[2]:.6f}<br>'
			'Conviction: %{customdata[3]:.6f}<extra></extra>'
		)
	)

	node_x = []
	node_y = []
	node_text = []
	node_sizes = []
	for node in graph.nodes():
		x, y = positions[node]
		node_x.append(x)
		node_y.append(y)
		node_text.append(f'{node}<br>Degree: {graph.degree(node)}')
		node_sizes.append(12 + graph.degree(node) * 2.5)

	node_trace = go.Scatter(
		x=node_x,
		y=node_y,
		mode='markers+text',
		text=list(graph.nodes()),
		textposition='top center',
		hovertemplate='%{hovertext}<extra></extra>',
		hovertext=node_text,
		marker={
			'size': node_sizes,
			'color': '#00b4d8',
			'line': {'width': 1, 'color': '#023047'}
		}
	)
	fig = go.Figure(data=[edge_trace, edge_hover_trace, node_trace])
	fig.update_layout(
		title={'text': "Bản đồ luồng hành vi mua sắm của khách hàng<br><sup><i>Giải thích: Mũi tên chỉ hướng mua sắm (Khởi điểm -> Mua kèm). Nút càng lớn thể hiện mặt hàng càng phổ biến.</i></sup>"},
		showlegend=False,
		xaxis={'showgrid': False, 'zeroline': False, 'showticklabels': False},
		yaxis={'showgrid': False, 'zeroline': False, 'showticklabels': False},
		template='plotly_white'
	)
	fig.write_html(output_path)


def build_heatmap_matrix(rules, top_n_heatmap_items):
	'''
	Tạo ma trận cho heatmap từ top item xuất hiện trong các rule mạnh.

	Cách làm:
	1. Tính điểm cho từng item dựa trên tổng `lift` của các rule có chứa item đó.
	2. Giữ lại top-N item theo điểm.
	3. Dựng ma trận item x item, mỗi ô giữ `lift` lớn nhất quan sát được.

	Lưu ý:
	- Không dựng ma trận full cho toàn bộ item vì sẽ rất lớn và khó đọc.
	- Dùng `max(lift)` để nhấn mạnh quan hệ mạnh nhất giữa hai item.
	'''
	item_scores = {}
	for record in rules:
		score = record['lift']
		for item in record['antecedent_items'] + record['consequent_items']:
			item_scores[item] = item_scores.get(item, 0) + score
	selected_items = [
		item for item, _ in sorted(item_scores.items(), key=lambda entry: entry[1], reverse=True)[:top_n_heatmap_items]
	]
	# Ma trận lưu nhiều metric để tooltip trong HTML hiển thị đầy đủ.
	matrix = {
		row: {
			col: {'lift': 0.0, 'confidence': 0.0, 'support': 0.0, 'conviction': 0.0}
			for col in selected_items
		}
		for row in selected_items
	}
	for record in rules:
		for antecedent in record['antecedent_items']:
			for consequent in record['consequent_items']:
				if antecedent in matrix and consequent in matrix[antecedent]:
					cell = matrix[antecedent][consequent]
					if record['lift'] > cell['lift']:
						cell['lift'] = record['lift']
						cell['confidence'] = record['confidence']
						cell['support'] = record['rule_support']
						cell['conviction'] = safe_float(record.get('conviction')) or 0.0
	return selected_items, matrix


def save_heatmap_png(rules, output_path, top_n_heatmap_items):
	'''
	Vẽ heatmap tĩnh từ ma trận lift.
	'''
	setup_matplotlib_font()
	labels, matrix = build_heatmap_matrix(rules, top_n_heatmap_items)
	values = [[matrix[row][col]['lift'] for col in labels] for row in labels]
	plt.figure(figsize=(12, 10))
	sns.heatmap(values, xticklabels=labels, yticklabels=labels, cmap='magma', annot=False)
	plt.suptitle('Bản đồ nhiệt: Cường độ liên kết (Lift) giữa các mặt hàng', fontsize=14, fontweight='bold')
	plt.title('Ô càng nóng/sáng thể hiện Lift cao (kích thích mua kèm mạnh hơn)', fontsize=10, fontstyle='italic')
	plt.xlabel('Vế phải (Consequents)')
	plt.ylabel('Vế trái (Antecedents)')
	plt.xticks(rotation=45, ha='right')
	plt.tight_layout()
	plt.savefig(output_path, dpi=200, facecolor='white')
	plt.close()


def save_heatmap_html(rules, output_path, top_n_heatmap_items):
	if go is None:
		write_placeholder_html(
			output_path,
			'Bản đồ nhiệt liên kết giữa các mặt hàng',
			'Plotly chưa được cài trong môi trường hiện tại nên HTML tương tác này được thay bằng trang mô tả.'
		)
		return

	'''
	Vẽ heatmap tương tác bằng Plotly.

	Bản HTML tiện cho việc đọc chính xác giá trị lift của từng ô.
	'''
	labels, matrix = build_heatmap_matrix(rules, top_n_heatmap_items)
	values = [[matrix[row][col]['lift'] for col in labels] for row in labels]
	custom = [
		[
			[
				matrix[row][col]['support'],
				matrix[row][col]['confidence'],
				matrix[row][col]['lift'],
				matrix[row][col]['conviction']
			]
			for col in labels
		]
		for row in labels
	]
	fig = go.Figure(
		data=go.Heatmap(
			z=values,
			x=labels,
			y=labels,
			colorscale='Magma',
			customdata=custom,
			hovertemplate=(
				'Vế trái: %{y}<br>'
				'Vế phải: %{x}<br>'
				'Support: %{customdata[0]:.6f}<br>'
				'Confidence: %{customdata[1]:.6f}<br>'
				'Lift: %{customdata[2]:.6f}<br>'
				'Conviction: %{customdata[3]:.6f}<extra></extra>'
			)
		)
	)
	fig.update_layout(
		title={'text': "Bản đồ nhiệt: Cường độ liên kết (Lift) giữa các mặt hàng<br><sup><i>Giải thích: Ô màu càng sáng/nóng (Lift > 1.5) chứng tỏ mặt hàng Vế trái kích thích mạnh việc mua mặt hàng Vế phải.</i></sup>"},
		xaxis_title='Vế phải (Consequents)',
		yaxis_title='Vế trái (Antecedents)',
		template='plotly_white'
	)
	fig.write_html(output_path)


def generate_visualizations(
	rule_records,
	frequent_itemset_records,
	output_dir,
	top_n_itemsets=20,
	top_n_rules=20,
	top_n_network_rules=20,
	top_n_heatmap_items=15
):
	'''
	Hàm điều phối toàn bộ pipeline visualization.

	Đầu vào là dữ liệu đã được chuẩn hóa trong `arm.py`, vì vậy module này
	không cần biết chi tiết Apriori chạy thế nào, chỉ cần tập trung vào việc
	chọn top-N và dựng biểu đồ.
	'''
	ensure_directory(output_dir)
	static_dir = os.path.join(output_dir, 'static')
	interactive_dir = os.path.join(output_dir, 'interactive')
	insights_dir = os.path.join(output_dir, 'insights')
	ensure_directory(static_dir)
	ensure_directory(interactive_dir)
	ensure_directory(insights_dir)
	if not VISUALIZATION_BACKEND_AVAILABLE:
		with open(os.path.join(insights_dir, 'visualizations_unavailable.txt'), 'w', encoding='utf-8') as handle:
			handle.write(
				'Interactive/static chart generation was skipped because one or more '
				'visualization dependencies are not installed in the current Python environment.'
			)
		return

	# Mỗi loại biểu đồ có tiêu chí chọn top-N riêng.
	# Ví dụ:
	# - Bar chart ưu tiên support_count lớn.
	# - Scatter plot ưu tiên rule vừa mạnh vừa đáng chú ý.
	# - Network graph ưu tiên rule có lift cao để mạng đỡ rối mà vẫn nhiều ý nghĩa.
	top_itemsets = top_records(frequent_itemset_records, ['support_count', 'itemset_size'], top_n_itemsets)
	top_rules = top_records(rule_records, ['confidence', 'lift', 'rule_support'], top_n_rules)
	top_network_rules = top_records(rule_records, ['lift', 'confidence', 'rule_support'], top_n_network_rules)

	save_bar_chart_png(top_itemsets, os.path.join(static_dir, 'frequent_itemsets_bar.png'))
	save_bar_chart_html(top_itemsets, os.path.join(interactive_dir, 'frequent_itemsets_bar.html'))
	save_scatter_png(top_rules, os.path.join(static_dir, 'rules_scatter.png'))
	save_scatter_html(top_rules, os.path.join(interactive_dir, 'rules_scatter.html'))
	save_network_png(top_network_rules, os.path.join(static_dir, 'rules_network.png'))
	save_network_html(top_network_rules, os.path.join(interactive_dir, 'rules_network.html'))
	save_heatmap_png(top_rules, os.path.join(static_dir, 'rules_heatmap.png'), top_n_heatmap_items)
	save_heatmap_html(top_rules, os.path.join(interactive_dir, 'rules_heatmap.html'), top_n_heatmap_items)

	# Đóng gói “luật vàng” để bạn dùng cho phần kết luận/đề xuất (mặc định 5–10 luật).
	golden_n = min(10, max(5, top_n_rules))
	golden_rules = export_golden_rules(rule_records, insights_dir, top_n=golden_n)
	save_scatter_golden_html(top_rules, golden_rules, os.path.join(interactive_dir, 'rules_scatter_golden.html'))
