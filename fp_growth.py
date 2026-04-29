import json
import os
import pickle
from collections import defaultdict
from itertools import combinations
from time import perf_counter

import config
from arm import (
	applymap,
	build_frequent_itemset_record,
	build_rule_record,
	calculate_rule_metrics,
	create_map,
	ensure_directory,
	format_metric,
	export_structured_outputs,
	load_data,
	passes_rule_filters,
)
from timing_wrapper import timeit
from visualize import generate_visualizations


MINSUP = config.MINSUP
RUN_VISUALIZATIONS = config.RUN_VISUALIZATIONS
TOP_N_ITEMSETS = config.TOP_N_ITEMSETS
TOP_N_RULES = config.TOP_N_RULES
TOP_N_NETWORK_RULES = config.TOP_N_NETWORK_RULES
TOP_N_HEATMAP_ITEMS = config.TOP_N_HEATMAP_ITEMS

DEFAULT_OUTPUT_DIR = config.FP_GROWTH_OUTPUT_DIR
DEFAULT_VISUALIZATION_DIR = config.FP_GROWTH_VIS_DIR


def _sorted_items(items, support_counts, strategy):
	"""
	Sắp xếp item theo chiến lược đã chọn để xây FP-tree.

	Chiến lược mặc định `support_desc` là cách chuẩn của FP-Growth vì nó giúp
	tăng khả năng dùng chung prefix, từ đó cây thường nhỏ hơn.
	"""
	if strategy == 'support_asc':
		return sorted(items, key=lambda item: (support_counts[item], item))
	if strategy == 'lexicographic':
		return sorted(items)
	return sorted(items, key=lambda item: (-support_counts[item], item))


class FPNode:
	"""
	Nút của FP-tree.

	Mỗi nút lưu item, count, parent và các con trực tiếp.
	`link` dùng để nối các nút cùng item trong header table.
	"""

	def __init__(self, item=None, count=0, parent=None):
		self.item = item
		self.count = count
		self.parent = parent
		self.children = {}
		self.link = None

	def increment(self, count):
		self.count += count


class FPTree:
	"""
	FP-tree tối giản phục vụ mining frequent itemsets.
	"""

	def __init__(self, support_counts, order_strategy='support_desc'):
		self.support_counts = dict(support_counts)
		self.order_strategy = order_strategy
		self.root = FPNode()
		self.header_table = {
			item: [count, None, None]
			for item, count in self.support_counts.items()
		}
		self.node_count = 1

	@classmethod
	def from_transactions(cls, transactions, support_counts, order_strategy='support_desc'):
		tree = cls(support_counts, order_strategy=order_strategy)
		for transaction in transactions:
			tree._insert_transaction(transaction, 1)
		return tree

	@classmethod
	def from_pattern_base(cls, pattern_base, support_counts, order_strategy='support_desc'):
		tree = cls(support_counts, order_strategy=order_strategy)
		for path, count in pattern_base:
			tree._insert_transaction(path, count)
		return tree

	def _insert_transaction(self, transaction, count):
		filtered = [item for item in transaction if item in self.header_table]
		if not filtered:
			return
		ordered = _sorted_items(filtered, self.support_counts, self.order_strategy)
		current = self.root
		for item in ordered:
			if item in current.children:
				child = current.children[item]
				child.increment(count)
			else:
				child = FPNode(item=item, count=count, parent=current)
				current.children[item] = child
				self.node_count += 1
				self._link_header(item, child)
			current = child

	def _link_header(self, item, node):
		count, head, tail = self.header_table[item]
		if head is None:
			self.header_table[item] = [count, node, node]
		else:
			tail.link = node
			self.header_table[item] = [count, head, node]

	def conditional_pattern_base(self, item):
		"""
		Sinh conditional pattern base cho một item theo các đường đi prefix.
		"""
		bases = []
		head = self.header_table[item][1]
		while head is not None:
			path = []
			parent = head.parent
			while parent is not None and parent.item is not None:
				path.append(parent.item)
				parent = parent.parent
			if path:
				bases.append((list(reversed(path)), head.count))
			head = head.link
		return bases

	def mine(self, prefix=(), minsup=1, stats=None):
		"""
		Khai phá toàn bộ frequent itemsets trong cây hiện tại.
		"""
		patterns = {}
		ordered_items = sorted(
			self.header_table.items(),
			key=lambda entry: (entry[1][0], entry[0])
		)
		for item, (support, _, _) in ordered_items:
			new_itemset = tuple(sorted(prefix + (item,)))
			patterns[new_itemset] = support

			pattern_base = self.conditional_pattern_base(item)
			if not pattern_base:
				continue

			conditional_support_counts = defaultdict(int)
			for path, count in pattern_base:
				for path_item in path:
					conditional_support_counts[path_item] += count

			conditional_support_counts = {
				path_item: count
				for path_item, count in conditional_support_counts.items()
				if count >= minsup
			}
			if not conditional_support_counts:
				continue

			conditional_tree = FPTree.from_pattern_base(
				pattern_base,
				conditional_support_counts,
				order_strategy=self.order_strategy,
			)
			if stats is not None:
				stats['conditional_tree_count'] += 1
				stats['conditional_tree_nodes'] += conditional_tree.node_count
			patterns.update(conditional_tree.mine(prefix=new_itemset, minsup=minsup, stats=stats))
		return patterns


def _transaction_support_counts(transactions):
	"""
	Đếm support cho toàn bộ item trong một lần quét dữ liệu.
	"""
	counts = defaultdict(int)
	for transaction in transactions:
		for item in transaction:
			counts[item] += 1
	return counts


def _build_frequent_itemset_levels(frequent_itemsets):
	"""
	Chuyển dict frequent itemsets sang cấu trúc theo level giống Apriori.
	"""
	levels = defaultdict(dict)
	for itemset, support in frequent_itemsets.items():
		levels[len(itemset)][tuple(sorted(itemset))] = support
	return [levels[size] for size in sorted(levels)]


def _generate_rules_from_itemsets(frequent_itemsets, total_transactions):
	"""
	Sinh association rules trực tiếp từ dict frequent itemsets.

	Cách này đơn giản hơn so với Apriori vì FP-Growth trả về itemsets dưới dạng
	dict phẳng thay vì phân theo từng level.
	"""
	rules = []
	support_lookup = {
		tuple(sorted(itemset)): support
		for itemset, support in frequent_itemsets.items()
	}
	for itemset, support in sorted(support_lookup.items(), key=lambda entry: (len(entry[0]), entry[1]), reverse=True):
		if len(itemset) < 2:
			continue
		for antecedent_size in range(1, len(itemset)):
			for antecedent in combinations(itemset, antecedent_size):
				antecedent = tuple(sorted(antecedent))
				consequent = tuple(sorted(set(itemset) - set(antecedent)))
				antecedent_support_count = support_lookup.get(antecedent)
				consequent_support_count = support_lookup.get(consequent)
				if antecedent_support_count is None or consequent_support_count is None:
					continue
				metrics = calculate_rule_metrics(
					support,
					antecedent_support_count,
					consequent_support_count,
					total_transactions,
				)
				if passes_rule_filters(metrics):
					rules.append({
						'antecedent': antecedent,
						'consequent': consequent,
						'metrics': metrics,
					})
	return rules


def _display_rules(rules, frequent_itemsets, reverse_map, total_transactions, output_dir):
	"""
	Ghi kết quả FP-Growth ra text/JSON/CSV với cùng schema như Apriori.
	"""
	ensure_directory(output_dir)
	structured_dir = os.path.join(output_dir, 'structured')
	ensure_directory(structured_dir)

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
	for itemset, support in sorted(frequent_itemsets.items(), key=lambda entry: (entry[1], len(entry[0])), reverse=True):
		frequent_itemset_records.append(
			build_frequent_itemset_record(itemset, support, reverse_map, total_transactions)
		)

	with open(os.path.join(output_dir, 'association_rules.txt'), 'w', encoding='utf-8') as handle:
		for record in rule_records:
			handle.write(
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
				+ '\n'
			)

	with open(os.path.join(output_dir, 'frequent_itemsets.txt'), 'w', encoding='utf-8') as handle:
		for record in frequent_itemset_records:
			handle.write(
				f'{record["itemset_label"]} '
				f'(support_count={record["support_count"]}, support={format_metric(record["support"])})\n'
			)

	export_structured_outputs(rule_records, frequent_itemset_records, structured_dir)
	return rule_records, frequent_itemset_records


def evaluate_tree_orderings(transactions_mapped, frequent_item_counts, strategies=None):
	"""
	Thử nhiều chiến lược sắp xếp item và chọn cây có số node nhỏ nhất.

	Đây là bước để “tối ưu cây” trên dữ liệu hiện tại.
	"""
	if strategies is None:
		strategies = ['support_desc', 'support_asc', 'lexicographic']
	reports = []
	for strategy in strategies:
		start = perf_counter()
		tree = FPTree.from_transactions(transactions_mapped, frequent_item_counts, order_strategy=strategy)
		reports.append({
			'strategy': strategy,
			'node_count': tree.node_count,
			'build_time_seconds': perf_counter() - start,
		})
	best = min(reports, key=lambda entry: (entry['node_count'], entry['build_time_seconds']))
	return best, reports


@timeit
def run_fp_growth_pipeline(
	data_path='data/groceries.csv',
	output_dir=DEFAULT_OUTPUT_DIR,
	visualization_dir=DEFAULT_VISUALIZATION_DIR,
	minsup=MINSUP,
	generate_plots=RUN_VISUALIZATIONS,
):
	"""
	Chạy toàn bộ pipeline FP-Growth và trả về các record đã chuẩn hóa.
	"""
	transactions, items = load_data(data_path)
	total_transactions = len(transactions)
	map_, reverse_map = create_map(items)
	pickle.dump(reverse_map, open('reverse_map.pkl', 'wb+'))

	transactions_mapped = [applymap(transaction, map_) for transaction in transactions]
	item_support_counts = _transaction_support_counts(transactions_mapped)
	frequent_item_counts = {
		item: count
		for item, count in item_support_counts.items()
		if count >= minsup
	}

	if not frequent_item_counts:
		return {
			'best_tree': None,
			'order_reports': [],
			'rule_records': [],
			'frequent_itemset_records': [],
			'frequent_itemsets': {},
			'rules': [],
		}

	best_tree_report, order_reports = evaluate_tree_orderings(transactions_mapped, frequent_item_counts)
	ordered_transactions = []
	for transaction in transactions_mapped:
		filtered = [item for item in transaction if item in frequent_item_counts]
		if filtered:
			ordered_transactions.append(_sorted_items(filtered, frequent_item_counts, best_tree_report['strategy']))

	primary_tree = FPTree.from_transactions(ordered_transactions, frequent_item_counts, order_strategy=best_tree_report['strategy'])
	stats = {
		'conditional_tree_count': 0,
		'conditional_tree_nodes': 0,
	}
	frequent_itemsets = primary_tree.mine(minsup=minsup, stats=stats)
	frequent_itemsets = {
		tuple(sorted(itemset)): support
		for itemset, support in frequent_itemsets.items()
		if support >= minsup
	}
	frequent_itemset_levels = _build_frequent_itemset_levels(frequent_itemsets)
	rules = _generate_rules_from_itemsets(frequent_itemsets, total_transactions)
	rule_records, frequent_itemset_records = _display_rules(rules, frequent_itemsets, reverse_map, total_transactions, output_dir)

	if generate_plots:
		generate_visualizations(
			rule_records,
			frequent_itemset_records,
			output_dir=visualization_dir,
			top_n_itemsets=TOP_N_ITEMSETS,
			top_n_rules=TOP_N_RULES,
			top_n_network_rules=TOP_N_NETWORK_RULES,
			top_n_heatmap_items=TOP_N_HEATMAP_ITEMS,
		)

	result = {
		'total_transactions': total_transactions,
		'best_tree': {
			'strategy': best_tree_report['strategy'],
			'node_count': primary_tree.node_count,
			'order_candidates': order_reports,
			'conditional_tree_count': stats['conditional_tree_count'],
			'conditional_tree_nodes': stats['conditional_tree_nodes'],
		},
		'frequent_itemsets': frequent_itemsets,
		'frequent_itemset_levels': frequent_itemset_levels,
		'rules': rules,
		'rule_records': rule_records,
		'frequent_itemset_records': frequent_itemset_records,
	}
	with open(os.path.join(output_dir, 'fp_growth_summary.json'), 'w', encoding='utf-8') as handle:
		json.dump(
			{
				'total_transactions': total_transactions,
				'best_tree': result['best_tree'],
				'frequent_itemset_count': len(frequent_itemsets),
				'rule_count': len(rules),
			},
			handle,
			indent=2,
		)
	return result


if __name__ == '__main__':
	result = run_fp_growth_pipeline()
	print('No of rules:', len(result['rules']), 'No of itemsets:', len(result['frequent_itemsets']))
	if result['best_tree']:
		print('Best FP-tree strategy:', result['best_tree']['strategy'])
		print('Best FP-tree node count:', result['best_tree']['node_count'])