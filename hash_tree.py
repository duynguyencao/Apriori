from timing_wrapper import timeit

class Node:
	'''
	Lớp biểu diễn một nút lá trong hash tree.

	Mỗi nút lá lưu trực tiếp các candidate itemset và support count của chúng.
	Khi chưa cần tách thêm nhánh, đây là nơi dữ liệu được giữ lại để truy vấn nhanh.
	'''

	def __init__(self, k, max_leaf_size, depth):
		'''
		Khởi tạo nút lá.

		Parameters
		----------
		k : int, optional
		    mẫu số của hàm băm.
		max_leaf_size : int, optional
		    số candidate tối đa mà một nút lá có thể chứa trước khi cần tách.
		depth : int, optional
		    độ sâu hiện tại của nút trong cây.
			
		'''
		self.max_leaf_size = max_leaf_size
		self.depth=depth
		self.children={}
		self.k=0
		self.isTree=False

	def add(self, candidate):
		'''
		Thêm một candidate vào nút lá.

		Parameters
		----------
		candidate : list
		    candidate itemset cần chèn vào.

		'''
		# Mỗi candidate được khởi tạo với support count = 0.
		self.children[tuple(candidate)] = 0


class Tree:
	'''
	Lớp biểu diễn hash tree dùng cho bài toán đếm support.

	Ý tưởng chính:
	- Candidate itemset không được duyệt tuyến tính toàn bộ mỗi lần kiểm tra.
	- Thay vào đó, ta phân candidate vào các bucket theo hàm băm.
	- Khi duyệt các subset của transaction, ta chỉ đi xuống đúng nhánh cần thiết.
	'''

	def __init__(self, c_list, k=3, max_leaf_size=3, depth=0):
		'''
		Hàm khởi tạo hash tree.

		Cây được tạo mới và chèn toàn bộ candidate trong `c_list` vào ngay từ đầu.
		Sau đó cây có thể được dùng lại để cập nhật support count khi quét transaction.

		Parameters
		----------
		c_list : list
		    danh sách itemset cần đưa vào cây.
		k : int, optional
			mẫu số của hàm băm.
		max_leaf_size : int, optional
		    số phần tử tối đa trong một nút lá trước khi tách.
		depth : int, optional
		    độ sâu hiện tại của cây con.
		
		Ví dụ
		-----
		>>> t=Tree(c_list=[[1,2], [2,3], [3,4]], k=3, max_leaf_size=3, depth=0)
		Cây được tạo và các itemset [1,2], [2,3], [3,4] được chèn vào.

		'''
		self.depth=depth
		self.children={}
		self.k=k
		self.max_leaf_size=max_leaf_size
		self.isTree=True
		self.c_length=len(c_list[0])
		self.build_tree(c_list)
		

	def update_tree(self):
		'''
		Tách nút lá nếu số candidate trong lá vượt quá `self.max_leaf_size`.

		Lưu ý:
		- Không được tách sâu hơn độ dài candidate itemset.
		- Mục tiêu là giữ số candidate trong mỗi lá đủ nhỏ để truy vấn nhanh.
		'''
		for child in self.children:
			if len(self.children[child].children) > self.max_leaf_size:
				# Chỉ tách khi vẫn còn chiều sâu hợp lệ để băm tiếp theo phần tử tiếp theo.
				if self.depth+1 < self.c_length:
					child=Tree(list(self.children[child].children.keys()), k=self.k, max_leaf_size=self.max_leaf_size, depth=self.depth+1)

	def build_tree(self, c_list):
		'''
		Xây dựng cây và chèn toàn bộ candidate itemset vào cây.

		Parameters
		----------
		c_list : list
		    danh sách itemset cần chèn.

		'''
		for candidate in c_list:
			# Bucket được xác định bởi phần tử tại độ sâu hiện tại mod k.
			if candidate[self.depth]%self.k not in self.children:
				self.children[candidate[self.depth]%self.k]=Node(k=self.k, max_leaf_size=self.max_leaf_size, depth=self.depth)
			self.children[candidate[self.depth]%self.k].add(candidate)
		self.update_tree()

	def check(self, candidate, update=False):
		'''
		Kiểm tra candidate có nằm trong cây hay không, đồng thời có thể cập nhật support count.

		Parameters
		----------
		candidate : list
		    candidate cần tra cứu.
		update : bool, optional
			Nếu là `True`, support count của candidate sẽ được tăng lên.

		Returns
		----------
		int
		Support count hiện tại của candidate.

		'''
		support=0
		if candidate[self.depth]%self.k in self.children:
			child = self.children[candidate[self.depth]%self.k]
			if child.isTree:
				# Nếu gặp cây con, tiếp tục đi sâu xuống theo cùng candidate.
				support = child.check(candidate)
			else:
				if tuple(candidate) in list(child.children.keys()):
					if update:
						# Chỉ tăng count khi candidate thực sự có trong lá.
						child.children[tuple(candidate)]+=1
					return child.children[tuple(candidate)]
				else:
					return 0
		return support

def generate_subsets(transaction, k):
	'''
		Sinh toàn bộ tập con kích thước `k` của một transaction bằng đệ quy.

		Parameters
		----------
		transaction : list
		    transaction cần sinh tập con.
		k : int
			số phần tử trong mỗi tập con.
		
		Returns
		----------
		list
		Danh sách các tập con sinh ra.
	'''
	res=[]
	n = len(transaction)
	# Sắp xếp trước để các subset được sinh ra theo thứ tự ổn định,
	# giúp so khớp nhất quán với candidate đã chuẩn hóa.
	transaction.sort()

	def recurse(transaction, k, i=0, curr=[]):
		'''
		Hàm đệ quy dùng để sinh tổ hợp.
		'''
		if k==1:
			for j in range(i,n):
				res.append(curr + [transaction[j]])
			return None
		for j in range(i,n-k+1):
			temp= curr+ [transaction[j]]
			recurse(transaction, k-1, j+1, temp[:])
	recurse(transaction, k)
	
	return res

if __name__=='__main__':
	temp_list=[[1,2,3],[2,3,4],[3,5,6],[4,5,6],[5,7,9],[7,8,9],[4,7,9]]
	t=Tree(temp_list, k=3, max_leaf_size=3, depth=0)