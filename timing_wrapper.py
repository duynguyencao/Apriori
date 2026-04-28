from time import time

def timeit(fn):
	'''
	Decorator đo thời gian chạy của hàm.

	Mục đích:
	- Theo dõi nhanh các bước tốn thời gian như đọc dữ liệu hoặc đếm support.
	- Giúp so sánh hiệu năng giữa các cách cài đặt khác nhau.
	'''
	def wrapper(*args, **kwargs):
		start = time()
		res = fn(*args, **kwargs)
		# Dung chuoi ASCII khi in ra terminal de tranh loi encoding tren mot so moi truong Windows.
		print(fn.__name__, "mat", time() - start, "giay.")
		return res
	return wrapper