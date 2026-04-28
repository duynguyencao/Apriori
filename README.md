# Association rules mining
Association rules mining using Apriori algorithm.

Course Assignment for CS F415- Data Mining @ BITS Pilani, Hyderabad Campus.

**Done under the guidance of Dr. Aruna Malapati, Assistant Professor, BITS Pilani, Hyderabad Campus.**

## Table of contents
* [Introduction](#introduction)
* [Data](#data)
* [Instructions to run the scripts](#instructions-to-run-the-scripts)
    * [Create the train matrix and the mappings](#create-the-train-matrix-and-the-mappings)
* [Important variables](#important-variables)
* [Hash Function](#hash-function)
* [Equations used](#equations-used)
* [Pre-processing done](#pre-processing-done)
* [Directory Structure:](#directory-structure-)
* [Prescribed format of output](#prescribed-format-of-output)
    * [Association Rules](#association-rules)
    * [Frequent itemsets](#frequent-itemsets)
* [Machine specs](#machine-specs-)
* [Results](#results)
* [Members](#members)

<small><i><a href='http://ecotrust-canada.github.io/markdown-toc/'>Table of contents generated with markdown-toc</a></i></small>

## Introduction
Association rules mining is a rule-based method for discovering interesting relations between variables in large databases. It is intended to identify strong rules discovered in databases using some measures of interestingness. This project reports the standard rule-quality metrics `support`, `confidence`, `lift`, and `conviction`.
**The main purpose of this project is to get an in depth understanding of how the Apriori algorithm works.**
We implemented support counting using hash trees. The difference between out approach is significant as demonstrated by the following run times (we used the same value of ```MINSUP``` and ```MIN_CONF``` for both) -

Support counting using brute force- ```22.5s```

Support counting using hash tree- ```5.9s ```

*For the sake of comparison, we have left in the code for the brute force method commented. Please feel free to uncomment it and try it out.*

*More on [Association rule learning](https://en.wikipedia.org/wiki/Association_rule_learning)*

## Data
We used the **Groceries Market Basket Dataset**, which can be found [here](http://www.sci.csueastbay.edu/~esuess/classes/Statistics_6620/Presentations/ml13/groceries.csv). The dataset contains **9835 transactions** by customers shopping for groceries. The data contains **169 unique items**. The data can be found in the folder **'data'**.

## Instructions to run the scripts
Run the following command:

##### Create the train matrix and the mappings
```python
python arm.py
```

## Important variables
```
MINSUP - Minimum support
HASH_DENOMINATOR - Denominator for the hash function (For support counting using hash tree)
MIN_CONF - Minimum confidence
MIN_LIFT - Minimum lift threshold for rule filtering
MIN_CONVICTION - Minimum conviction threshold for rule filtering
RUN_VISUALIZATIONS - Enable or disable visualization generation
TOP_N_ITEMSETS - Number of frequent itemsets shown in the bar chart
TOP_N_RULES - Number of rules shown in the scatter plot
TOP_N_NETWORK_RULES - Number of rules used to build the network graph
TOP_N_HEATMAP_ITEMS - Number of items retained in the heatmap matrix
```

## Hash Function
We have used hash function of the followinng format-
```x(mod)k```
where k is chosen by the user.

## Equations used
```
confidence(X->Y) = support(X U Y) / support(X)
support(X, Y) = support count(X, Y) / total dataset size
lift(X->Y) = confidence(X->Y) / support(Y)
conviction(X->Y) = (1 - support(Y)) / (1 - confidence(X->Y))
```


## Pre-processing done
The csv file was read transaction by transaction and each transaction was saved as a list.
A mapping was created from the unique items in the dataset to integers so that each item corresponded to a unique integer.
The entire data was mapped to integers to reduce the storage and computational requirement.
A reverse mapping was created from the integers to the items, so that the item names could be written in the final output file.

## Directory Structure
```
association-rule-mining-apriori/
+-- data
|   +-- groceries.csv (original data file containing transactions)
+--  arm.py(python script to read the data, mine frequent itemsets and interesting rules)
+--  hash_tree.py(python file containing the Tree and Node classes used to build the hash tree for support counting)
+--  timing_wrapper.py(python decorator used to measure execution time of functions)
+--  l_final.pkl(all the frequent itemsets in pickled format)
+--  outputs(destination to save the outputs generated)
|   +-- frequent_itemsets.txt(all the frequent itemsets presented in the prescribed format)
|   +-- association_rules.txt(all the interesting association rules mined and presented in the prescribed format)
|   +-- structured(CSV/JSON outputs for downstream visualization)
+--  visualizations(static PNG and interactive HTML charts)
+--  results(folder containing the results of this project)
+--  reverse_map.pkl(mapping from items to index in pickled format)
+--  requirements.txt
```

## Prescribed format of output
##### Association Rules
```
Precedent (itemset (support count)) ---> Antecedent (itemset (support count)) - confidence value

Current output format:
Antecedent (support count) ---> Consequent (support count) | rule_support_count | support | confidence | lift | conviction
```

Rules are retained only if they satisfy all configured thresholds:

- `confidence > MIN_CONF`
- `lift > MIN_LIFT`
- `conviction > MIN_CONVICTION`

Current defaults:

- `MIN_CONF = 0.5`
- `MIN_LIFT = 1.2`
- `MIN_CONVICTION = 1.2`

## Visualization
The project now generates both **static PNG charts** and **interactive HTML charts** when `python arm.py` finishes.

Libraries used:

- `matplotlib` and `seaborn` for static chart rendering
- `plotly` for interactive HTML visualizations
- `networkx` for the network graph layout

Generated chart files:

- `visualizations/static/frequent_itemsets_bar.png`
- `visualizations/static/rules_scatter.png`
- `visualizations/static/rules_network.png`
- `visualizations/static/rules_heatmap.png`
- `visualizations/interactive/frequent_itemsets_bar.html`
- `visualizations/interactive/rules_scatter.html`
- `visualizations/interactive/rules_network.html`
- `visualizations/interactive/rules_heatmap.html`

Generated structured outputs:

- `outputs/structured/frequent_itemsets.csv`
- `outputs/structured/frequent_itemsets.json`
- `outputs/structured/association_rules.csv`
- `outputs/structured/association_rules.json`
- `outputs/structured/mining_results.json`

Why these visualizations are appropriate:

- **Bar chart**: shows the strongest frequent itemsets quickly.
- **Scatter plot**: shows the global distribution of association rules across `support`, `confidence`, `lift`, and `conviction`.
- **Network graph**: highlights item-to-item relationships induced by strong rules.
- **Heatmap**: summarizes the strongest antecedent/consequent item interactions.

To keep charts readable, the code limits each chart with configurable top-N values rather than plotting every itemset and rule.

##### Frequent itemsets
```
Frequent itemset (support count)
```


## Machine specs
Processor: i7-7500U

Ram: 16 GB DDR4

OS: Ubuntu 16.04 LTS

## Results

| Confidence/Support | No. of itemsets | No of rules |
|---------------------|-------|--------|
| High confidence(MIN_CONF=0.5) High support count(MINSUP=60)               | 725  |  60      |
| Low confidence(MIN_CONF=0.1) High support count(MINSUP=60)              | 725   |    1189    |
| High confidence(MIN_CONF=0.5) Low support count(MINSUP=10)              | 11390   |    4187    |
| Low confidence(MIN_CONF=0.1) Low support count(MINSUP=10)              | 11390   |    35196    |

All the frequent itemsets and rules generated using the above mentioned configurations can be found in the 'results' folder.

## Members
[Shubham Jha](http://github.com/shubhamjha97)

[Praneet Mehta](http://github.com/praneetmehta)

[Abhinav Jain](http://github.com/abhinav1112)