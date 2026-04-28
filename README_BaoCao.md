## Top 5 “Luật vàng” (tự động chắt lọc)

Dữ liệu được lấy từ `visualizations/insights/golden_rules.txt` sau khi chạy `python arm.py`.

### 1) butter, whipped/sour cream → whole milk
- **Luật**: butter, whipped/sour cream → whole milk  
  **Support**: 0.006711 | **Confidence**: 0.660000 | **Lift**: 2.583008 | **Conviction**: 2.189659
- **Action/Hành động**: đặt “whipped/sour cream” cạnh “whole milk” và gợi ý combo “bơ + sữa” trong khung giờ cao điểm.

### 2) butter, yogurt → whole milk
- **Luật**: butter, yogurt → whole milk  
  **Support**: 0.009354 | **Confidence**: 0.638889 | **Lift**: 2.500387 | **Conviction**: 2.061648
- **Action/Hành động**: tạo cụm “bữa sáng” (yogurt/butter/whole milk) cùng một dãy kệ và chạy giảm giá mua kèm.

### 3) butter, root vegetables → whole milk
- **Luật**: butter, root vegetables → whole milk  
  **Support**: 0.008236 | **Confidence**: 0.637795 | **Lift**: 2.496107 | **Conviction**: 2.055423
- **Action/Hành động**: đặt POS/standee “gợi ý nấu ăn” tại khu rau củ (root vegetables) kèm đề xuất mua thêm whole milk/butter.

### 4) curd, tropical fruit → whole milk
- **Luật**: curd, tropical fruit → whole milk  
  **Support**: 0.006507 | **Confidence**: 0.633663 | **Lift**: 2.479936 | **Conviction**: 2.032240
- **Action/Hành động**: thiết kế combo “trái cây + curd + sữa” (healthy snack) và hiển thị gợi ý ở khu trái cây nhiệt đới.

### 5) butter, tropical fruit → whole milk
- **Luật**: butter, tropical fruit → whole milk  
  **Support**: 0.006202 | **Confidence**: 0.622449 | **Lift**: 2.436047 | **Conviction**: 1.971877
- **Action/Hành động**: đặt gợi ý mua kèm whole milk trên bảng giá/kệ của tropical fruit (cross-sell tại điểm chạm).

