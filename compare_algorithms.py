import csv
import json
import os
from collections import defaultdict
from itertools import combinations
from time import perf_counter

from arm import (
	HASH_DENOMINATOR,
	MINSUP,
	applymap,
	apriori_gen,
	calculate_rule_metrics,
	create_map,
	load_data,
	passes_rule_filters,
	build_rule_record,
	build_frequent_itemset_record,
	format_metric,
)
from hash_tree import Tree, generate_subsets
from fp_growth import (
	FPTree,
	_generate_rules_from_itemsets,
	_transaction_support_counts,
	evaluate_tree_orderings,
)


OUTPUT_DIR = os.path.join('outputs', 'comparison')


def _ensure_directory(path):
	os.makedirs(path, exist_ok=True)


def _count_hash_tree_nodes(tree_or_node):
	"""
	Đếm số node trong hash tree theo cấu trúc hiện tại của dự án.

	Tree Apriori chỉ dùng 1 lớp node bucket ở phía trên, nhưng hàm này vẫn
	viết theo kiểu đệ quy để giữ an toàn nếu hash_tree thay đổi trong tương lai.
	"""
	if hasattr(tree_or_node, 'isTree') and tree_or_node.isTree:
		total = 1
		for child in tree_or_node.children.values():
			total += _count_hash_tree_nodes(child)
		return total
	total = 1
	if hasattr(tree_or_node, 'children'):
		total += len(tree_or_node.children)
	return total


def _subset_with_stats(c_list, transactions):
	"""
	Đếm support cho candidate bằng hash tree và trả thêm số node của cây.
	"""
	if not c_list:
		return {}, 0
	tree = Tree(c_list, k=HASH_DENOMINATOR, max_leaf_size=100)
	for transaction in transactions:
		subsets = generate_subsets(transaction, len(c_list[0]))
		for sub in subsets:
			tree.check(sub, update=True)
	candidate_counts = {}
	for candidate in c_list:
		candidate_counts[tuple(candidate)] = tree.check(candidate, update=False)
	return candidate_counts, _count_hash_tree_nodes(tree)


def _apriori_with_stats(data_path, minsup=MINSUP):
	"""
	Chạy Apriori theo đúng luồng hiện có nhưng đo thêm node và thời gian.
	"""
	transactions, items = load_data(data_path)
	total_transactions = len(transactions)
	map_, reverse_map = create_map(items)
	transactions_mapped = [applymap(transaction, map_) for transaction in transactions]
	items_mapped = [[item] for item in range(len(items))]

	level_node_counts = []
	start = perf_counter()
	current_counts, node_count = _subset_with_stats(items_mapped, transactions_mapped)
	level_node_counts.append(node_count)
	current_level = {
		tuple(candidate): support
		for candidate, support in current_counts.items()
		if support > minsup
	}
	frequent_levels = [current_level]
	while current_level:
		candidates = apriori_gen(list(current_level.keys()))
		if not candidates:
			break
		candidate_counts, node_count = _subset_with_stats(candidates, transactions_mapped)
		level_node_counts.append(node_count)
		current_level = {
			tuple(sorted(candidate)): support
			for candidate, support in candidate_counts.items()
			if support > minsup
		}
		if current_level:
			frequent_levels.append(current_level)
	mining_time_seconds = perf_counter() - start

	rule_start = perf_counter()
	rules = []
	for k_itemset in frequent_levels:
		if not k_itemset:
			continue
		k = len(next(iter(k_itemset.keys())))
		if k == 1:
			continue
		for itemset, support in k_itemset.items():
			for antecedent_size in range(1, len(itemset)):
				for antecedent in combinations(itemset, antecedent_size):
					antecedent = tuple(sorted(antecedent))
					consequent = tuple(sorted(set(itemset) - set(antecedent)))
					antecedent_support_count = None
					consequent_support_count = None
					for level in frequent_levels:
						if antecedent in level:
							antecedent_support_count = level[antecedent]
						if consequent in level:
							consequent_support_count = level[consequent]
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
	rule_time_seconds = perf_counter() - rule_start

	frequent_itemset_count = sum(len(level) for level in frequent_levels)
	peak_tree_nodes = max(level_node_counts) if level_node_counts else 0
	total_tree_nodes = sum(level_node_counts)
	return {
		'total_transactions': total_transactions,
		'frequent_levels': frequent_levels,
		'frequent_itemset_count': frequent_itemset_count,
		'rules': rules,
		'rule_count': len(rules),
		'mining_time_seconds': mining_time_seconds,
		'rule_time_seconds': rule_time_seconds,
		'total_time_seconds': mining_time_seconds + rule_time_seconds,
		'peak_tree_nodes': peak_tree_nodes,
		'total_tree_nodes': total_tree_nodes,
	}


def _fp_growth_with_stats(data_path, minsup=MINSUP):
	"""
	Chạy FP-Growth theo cây tối ưu nhất và đo thêm node/time.
	"""
	transactions, items = load_data(data_path)
	total_transactions = len(transactions)
	map_, reverse_map = create_map(items)
	transactions_mapped = [applymap(transaction, map_) for transaction in transactions]
	item_support_counts = _transaction_support_counts(transactions_mapped)
	frequent_item_counts = {
		item: count
		for item, count in item_support_counts.items()
		if count >= minsup
	}
	best_tree_report, order_reports = evaluate_tree_orderings(transactions_mapped, frequent_item_counts)
	ordered_transactions = []
	for transaction in transactions_mapped:
		filtered = [item for item in transaction if item in frequent_item_counts]
		if filtered:
			ordered_transactions.append(
				sorted(filtered, key=lambda item: (-frequent_item_counts[item], item))
				if best_tree_report['strategy'] == 'support_desc'
				else sorted(filtered, key=lambda item: (frequent_item_counts[item], item))
				if best_tree_report['strategy'] == 'support_asc'
				else sorted(filtered)
			)

	start = perf_counter()
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
	mining_time_seconds = perf_counter() - start

	rule_start = perf_counter()
	rules = _generate_rules_from_itemsets(frequent_itemsets, total_transactions)
	rule_time_seconds = perf_counter() - rule_start

	return {
		'total_transactions': total_transactions,
		'frequent_itemsets': frequent_itemsets,
		'frequent_itemset_count': len(frequent_itemsets),
		'rules': rules,
		'rule_count': len(rules),
		'mining_time_seconds': mining_time_seconds,
		'rule_time_seconds': rule_time_seconds,
		'total_time_seconds': mining_time_seconds + rule_time_seconds,
		'peak_tree_nodes': primary_tree.node_count,
		'total_tree_nodes': primary_tree.node_count + stats['conditional_tree_nodes'],
		'best_tree': {
			'strategy': best_tree_report['strategy'],
			'node_count': best_tree_report['node_count'],
			'order_candidates': order_reports,
			'conditional_tree_count': stats['conditional_tree_count'],
			'conditional_tree_nodes': stats['conditional_tree_nodes'],
		},
	}


def _space_complexity_text(algorithm_name):
	if algorithm_name == 'Apriori':
		return 'O(max(|Ck|) + hash tree size)'
	return 'O(size of FP-tree + conditional FP-trees)'


def _time_complexity_text(algorithm_name):
	if algorithm_name == 'Apriori':
		return 'O(sum_k |Ck| * |T| * k)'
	return 'O(|T| * avg_transaction_length + recursive conditional mining)'


def _write_reports(apriori_result, fp_growth_result):
	_ensure_directory(OUTPUT_DIR)
	comparison_rows = [
		{
			'algorithm': 'Apriori',
			'mining_time_seconds': apriori_result['mining_time_seconds'],
			'rule_time_seconds': apriori_result['rule_time_seconds'],
			'total_time_seconds': apriori_result['total_time_seconds'],
			'peak_tree_nodes': apriori_result['peak_tree_nodes'],
			'total_tree_nodes': apriori_result['total_tree_nodes'],
			'frequent_itemset_count': apriori_result['frequent_itemset_count'],
			'rule_count': apriori_result['rule_count'],
			'time_complexity': _time_complexity_text('Apriori'),
			'space_complexity': _space_complexity_text('Apriori'),
			'optimal_tree_strategy': '',
		},
		{
			'algorithm': 'FP-Growth',
			'mining_time_seconds': fp_growth_result['mining_time_seconds'],
			'rule_time_seconds': fp_growth_result['rule_time_seconds'],
			'total_time_seconds': fp_growth_result['total_time_seconds'],
			'peak_tree_nodes': fp_growth_result['peak_tree_nodes'],
			'total_tree_nodes': fp_growth_result['total_tree_nodes'],
			'frequent_itemset_count': fp_growth_result['frequent_itemset_count'],
			'rule_count': fp_growth_result['rule_count'],
			'time_complexity': _time_complexity_text('FP-Growth'),
			'space_complexity': _space_complexity_text('FP-Growth'),
			'optimal_tree_strategy': fp_growth_result['best_tree']['strategy'],
		},
	]

	with open(os.path.join(OUTPUT_DIR, 'algorithm_comparison.json'), 'w', encoding='utf-8') as handle:
		json.dump(comparison_rows, handle, ensure_ascii=False, indent=2)

	with open(os.path.join(OUTPUT_DIR, 'algorithm_comparison.csv'), 'w', newline='', encoding='utf-8') as handle:
		fieldnames = [
			'algorithm',
			'mining_time_seconds',
			'rule_time_seconds',
			'total_time_seconds',
			'peak_tree_nodes',
			'total_tree_nodes',
			'frequent_itemset_count',
			'rule_count',
			'time_complexity',
			'space_complexity',
			'optimal_tree_strategy',
		]
		writer = csv.DictWriter(handle, fieldnames=fieldnames)
		writer.writeheader()
		for row in comparison_rows:
			writer.writerow(row)

	better_by_time = 'FP-Growth' if fp_growth_result['total_time_seconds'] < apriori_result['total_time_seconds'] else 'Apriori'
	better_by_space = 'FP-Growth' if fp_growth_result['peak_tree_nodes'] < apriori_result['peak_tree_nodes'] else 'Apriori'
	if better_by_time == better_by_space:
		winner = better_by_time
	else:
		winner = f'Khac nhau: nhanh hon la {better_by_time}, cay gon hon la {better_by_space}'

	summary_lines = [
		'Comparison of Apriori vs FP-Growth',
		f"Apriori: mining={format_metric(apriori_result['mining_time_seconds'])}s | total={format_metric(apriori_result['total_time_seconds'])}s | peak_nodes={apriori_result['peak_tree_nodes']} | total_nodes={apriori_result['total_tree_nodes']}",
		f"FP-Growth: mining={format_metric(fp_growth_result['mining_time_seconds'])}s | total={format_metric(fp_growth_result['total_time_seconds'])}s | peak_nodes={fp_growth_result['peak_tree_nodes']} | total_nodes={fp_growth_result['total_tree_nodes']} | optimal_tree={fp_growth_result['best_tree']['strategy']}",
		f'Winner: {winner}',
	]
	with open(os.path.join(OUTPUT_DIR, 'algorithm_comparison.txt'), 'w', encoding='utf-8') as handle:
		handle.write('\n'.join(summary_lines) + '\n')


def run_comparison(data_path='data/groceries.csv', minsup=MINSUP):
	apriori_result = _apriori_with_stats(data_path, minsup=minsup)
	fp_growth_result = _fp_growth_with_stats(data_path, minsup=minsup)
	_write_reports(apriori_result, fp_growth_result)
	return apriori_result, fp_growth_result


if __name__ == '__main__':
	apriori_result, fp_growth_result = run_comparison()
	print('Apriori total time:', format_metric(apriori_result['total_time_seconds']))
	print('FP-Growth total time:', format_metric(fp_growth_result['total_time_seconds']))
	print('FP-Growth best tree strategy:', fp_growth_result['best_tree']['strategy'])