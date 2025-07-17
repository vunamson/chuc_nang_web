# delete_produc.py với API Bulk và comment tiếng Việt

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import islice

# Hàm tiện ích: chia một iterable thành các batch nhỏ có kích thước cố định
# Ví dụ: chunked([1,2,3,4,5], 2) -> [[1,2], [3,4], [5]]
def chunked(iterable, size):
    it = iter(iterable)
    while True:
        batch = list(islice(it, size))
        if not batch:
            return
        yield batch

class WooDeleter:
    """
    Lớp hỗ trợ xóa và cập nhật hàng loạt sản phẩm qua WooCommerce REST API Bulk endpoints
    """
    def __init__(self, base_url: str, consumer_key: str, consumer_secret: str, max_workers: int = 10, batch_size: int = 100):
        # Thiết lập URL cơ bản, phiên làm việc để tái sử dụng kết nối HTTP
        self.base = base_url.rstrip('/')
        self.session = requests.Session()                     # reuse TCP connection
        self.auth = {'consumer_key': consumer_key, 'consumer_secret': consumer_secret}
        self.max_workers = max_workers                         # số worker cho ThreadPool
        self.batch_size = batch_size                           # kích thước batch cho Bulk API

    def _request(self, method, path, params=None, json=None, timeout=60):
        # Gửi request HTTP chung cho GET/POST/DELETE/PUT đến WooCommerce API
        p = params.copy() if params else {}
        p.update(self.auth)
        url = f"{self.base}/wp-json/wc/v3{path}"
        resp = self.session.request(method, url, params=p, json=json, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    def list_products_by_category(self, cat_id):
        """
        Lấy danh sách tất cả sản phẩm (object) thuộc category cho trước
        Trả về list các dict sản phẩm
        """
        all_items = []
        page = 1
        while True:
            items = self._request('GET', '/products', {'category': cat_id, 'per_page': 100, 'page': page})
            if not items:
                break
            all_items.extend(items)
            page += 1
        return all_items

    def batch_delete_products(self, ids: list[int]):
        """
        Xóa hàng loạt sản phẩm theo danh sách ID
        Sử dụng endpoint /products/batch với action 'delete'
        """
        data = {'delete': ids, 'force': True}
        return self._request('POST', '/products/batch', json=data)

    def batch_update_products(self, payload: list[dict]):
        """
        Cập nhật hàng loạt sản phẩm (ví dụ: thay đổi categories)
        Mỗi item trong payload là dict {'id': pid, 'categories':[{'id':cid},...]}
        """
        data = {'update': payload}
        return self._request('POST', '/products/batch', json=data)

    def delete_category(self, cat_id: int):
        """
        Xóa một category sản phẩm (taxonomy) theo ID
        """
        return self._request('DELETE', f'/products/categories/{cat_id}', {'force': True})


def run_delete(base_url, consumer_key, consumer_secret, max_workers, categories):
    """
    Hàm chính: hiển thị menu lựa chọn và thực thi các thao tác xóa/cập nhật
    Tham số:
      - base_url, consumer_key, consumer_secret: thông tin kết nối API
      - max_workers: số luồng tối đa cho ThreadPool
      - categories: danh sách ID category khả dụng (được truyền từ main)
    """
    wo = WooDeleter(base_url, consumer_key, consumer_secret, max_workers, batch_size=100)

    # Hiển thị menu chức năng
    menu = '''
=== XÓA SẢN PHẨM (Delete Products) ===
1. Remove association khỏi Category A (nếu rỗng thì xóa product + delete Category A)
2. Xóa hẳn products trong Category A + delete Category A
3. Xóa product theo ID (xóa hẳn)
4. Remove association theo ID trong Category
'''
    print(menu)
    choice = input("Chọn (1-4): ").strip()

    # NẾU choice 1 hoặc 2, cần cho người dùng chọn danh sách category
    if choice in {'1', '2'}:
        print("Danh sách Category khả dụng:")
        for idx, cid in enumerate(categories, 1):
            print(f"{idx}. {cid}")
        sel = input("Chọn categories (vd: 1,3,5): ").strip()
        idxs = [int(x)-1 for x in sel.split(',') if x.strip().isdigit()]
        selected = [categories[i] for i in idxs if 0 <= i < len(categories)]
        if not selected:
            print("❗ Chưa chọn category nào. Thoát.")
            return

    # THAO TÁC 1: remove association khỏi category và xóa orphan products
    if choice == '1':
        for cat in selected:
            print(f"\n⏳ Xử lý Category {cat} …")
            prods = wo.list_products_by_category(cat)
            to_update, to_delete = [], []

            # Phân loại: sản phẩm có nhiều category thì update, khác thì delete
            for p in prods:
                pid = p['id']
                cats = [c['id'] for c in p['categories']]
                if len(cats) > 1:
                    # giữ các category khác, bỏ cat hiện tại
                    new_cats = [c for c in cats if c != cat]
                    to_update.append({'id': pid, 'categories': [{'id': cid} for cid in new_cats]})
                else:
                    # orphan -> xóa hẳn
                    to_delete.append(pid)

            # Bulk cập nhật categories
            for batch in chunked(to_update, wo.batch_size):
                wo.batch_update_products(batch)
                print(f"✔ Updated categories cho {len(batch)} products")

            # Bulk xóa products orphan
            for batch in chunked(to_delete, wo.batch_size):
                wo.batch_delete_products(batch)
                print(f"✔ Deleted {len(batch)} orphan products")

            # Cuối cùng xóa category trống
            wo.delete_category(cat)
            print(f"✔ Deleted Category {cat}")

    # THAO TÁC 2: xóa hẳn tất cả sản phẩm trong category và xóa category
    elif choice == '2':
        for cat in selected:
            print(f"\n⏳ Xóa hẳn products & Category {cat} …")
            prods = wo.list_products_by_category(cat)
            ids = [p['id'] for p in prods]
            # Bulk delete theo batch
            for batch in chunked(ids, wo.batch_size):
                wo.batch_delete_products(batch)
                print(f"✔ Deleted {len(batch)} products")
            # Xóa category sau cùng
            wo.delete_category(cat)
            print(f"✔ Deleted Category {cat}")

    # THAO TÁC 3: xóa sản phẩm theo list ID nhập tay
    elif choice == '3':
        print("Nhập danh sách Product ID (mỗi ID 1 dòng), blank để kết thúc:")
        ids = []
        while True:
            line = input().strip()
            if not line:
                break
            if line.isdigit():
                ids.append(int(line))
        # Bulk delete theo batch
        for batch in chunked(ids, wo.batch_size):
            wo.batch_delete_products(batch)
            print(f"✔ Deleted {len(batch)} products")

    # THAO TÁC 4: remove association theo các cặp product/category
    elif choice == '4':
        print("Nhập mỗi dòng: product_id,cat_id1,cat_id2,... (blank để kết thúc):")
        updates, deletes = [], []
        while True:
            line = input().strip()
            if not line:
                break
            parts = [int(x) for x in line.split(',') if x.strip().isdigit()]
            pid, rem = parts[0], parts[1:]
            prod = wo._request('GET', f'/products/{pid}')
            current = [c['id'] for c in prod['categories']]
            new = [c for c in current if c not in rem]
            if new:
                updates.append({'id': pid, 'categories': [{'id': cid} for cid in new]})
            else:
                deletes.append(pid)

        # Bulk update/remove
        for batch in chunked(updates, wo.batch_size):
            wo.batch_update_products(batch)
            print(f"✔ Updated {len(batch)} products")
        for batch in chunked(deletes, wo.batch_size):
            wo.batch_delete_products(batch)
            print(f"✔ Deleted {len(batch)} products")

    else:
        print("❗ Lựa chọn không hợp lệ.")
