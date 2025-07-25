# feed_product.py

import csv
import json
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from woocommerce import API
from io import BytesIO
from PIL import Image

# Thiết lập cấu hình logging để theo dõi quá trình thực thi
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class WooHelper:
    """
    Lớp hỗ trợ tương tác với WooCommerce API,
    bao gồm lấy và tạo category, cũng như gửi batch tạo sản phẩm.
    """
    def __init__(self, base_url, consumer_key, consumer_secret):
        # Khởi tạo kết nối API
        self.wcapi = API(
            url=base_url,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            version="wc/v3",
            timeout=30
        )
        # Bản đồ lưu trữ category đã có: tên -> id
        self.cat_map = {}

    def prefetch_categories(self):
        """
        Tải trước toàn bộ category hiện có trong WooCommerce vào self.cat_map
        để tránh gọi API nhiều lần cho từng tên category.
        """
        page = 1
        per_page = 100
        while True:
            resp = self.wcapi.get(
                f"products/categories?page={page}&per_page={per_page}"
            ).json()
            if not resp:
                break
            # Lưu mỗi category vào bản đồ
            for cat in resp:
                self.cat_map[cat['name']] = cat['id']
            page += 1
        logging.info(f"Đã load {len(self.cat_map)} categories từ store")

    def batch_create_categories(self, names):
        """
        Tạo nhiều category mới trong 1 request batch
        và cập nhật self.cat_map sau khi tạo thành công.
        """
        # Chuẩn bị payload 'create' từ danh sách tên category
        create_list = [{'name': name} for name in names]
        if not create_list:
            return
        payload = {'create': create_list}
        resp = self.wcapi.post('products/categories/batch', payload).json()
        # Cập nhật map với category vừa tạo
        for cat in resp.get('create', []):
            self.cat_map[cat['name']] = cat['id']
        logging.info(f"Đã tạo {len(resp.get('create', []))} category mới")

    def get_category_id(self, name):
        """
        Lấy id từ tên category trong self.cat_map.
        """
        return self.cat_map.get(name)

    def batch_create_products(self, products):
        """
        Gửi request batch để tạo nhiều sản phẩm cùng lúc.
        """
        payload = {'create': products}
        resp = self.wcapi.post('products/batch', payload).json()
        # logging.info(f"Batch response: {json.dumps(resp, indent=4)}")  # Kiểm tra phản hồi API
        return resp


def read_csv(csv_path):
    """
    Đọc toàn bộ dòng từ file CSV đầu vào,
    trả về list các dict, mỗi dict tương ứng 1 dòng.
    """
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

def chunk_list(lst, chunk_size):
    """
    Chia list lst thành các chunk có kích thước tối đa chunk_size.
    """
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i+chunk_size]

def build_product_payload(row, helper):
    """
    Tạo payload dict cho từng dòng CSV:
    - Xử lý category (tách, tạo mới nếu cần)
    - Xử lý images (split 'src')
    - Lưu các trường cơ bản: type, price, description, name
    """
    # Xử lý danh sách category (split theo dấu ,)
    cat_names = [c.strip() for c in row['Categories'].split(',') if c.strip()]
    # Tìm những category chưa có trong map
    missing = [name for name in cat_names if name not in helper.cat_map]
    # Tạo batch category mới nếu có
    if missing:
        helper.batch_create_categories(missing)
    # Lấy id tương ứng
    cat_ids = [helper.get_category_id(name) for name in cat_names]

    # Xử lý danh sách ảnh, tách theo ký tự ',,'
    img_urls = [u.strip() for u in row['Images'].split(',,') if u.strip()]
    # images = [{'fifu_image_url': url} for url in img_urls]

    # Build payload product
    payload = {
        'status': 'publish',
        'type': row.get('Type', 'simple'),                   # Loại sản phẩm
        'regular_price': row.get('Regular price', ''),        # Giá bán
        'description': row.get('Description', ''),            # Mô tả dài
        'categories': [{'id': cid} for cid in cat_ids if cid],# Danh sách category id
        # 'images': images,                                     # Hình ảnh
        'name': row.get('Name', row.get('SKU', '')),         # Tên sản phẩm hoặc fallback SKU
    }
    meta = []
    for idx, url in enumerate(img_urls):
        if idx == 0:
            meta.append({
                'key': 'fifu_image_url',
                'value': url
            })
            # meta.append({
            #     'key': 'fifu_list_url',
            #     'value': url
            # })
        else:
            index_image = idx-1
            meta.append({
                'key': f'fifu_image_url_{index_image}',
                'value': url
            })
            # meta.append({
            #     'key': f'fifu_list_url_{index_image}',
            #     'value': url
            # })
    if meta:
        payload['meta_data'] = meta

    if len(img_urls) == 1:
        # Nếu chỉ có 1 ảnh, đặt giá trị fifu_list_url là ảnh đó
        payload['meta_data'].append({
            'key': 'fifu_list_url',
            'value': img_urls[0]
        })
    elif len(img_urls) > 1:
        # Nếu có nhiều ảnh, nối các link bằng dấu '|'
        payload['meta_data'].append({
            'key': 'fifu_list_url',
            'value': '|'.join(img_urls)
        })
    return payload

def feed_products(csv_path, base_url, ck, cs,
                  batch_size=80, max_workers=3, throttle=1.0):
    """
    Chạy quy trình import:
    1) Prefetch tất cả category
    2) Đọc CSV thành rows
    3) Build payloads và tự động tạo category thiếu
    4) Chia thành batches và tạo song song
    5) Throttling giữa các batch
    """
    helper = WooHelper(base_url, ck, cs)
    helper.prefetch_categories()

    # Đọc dữ liệu từ file CSV
    rows = read_csv(csv_path)
    logging.info(f"Đã load {len(rows)} dòng từ CSV")

    # Build payload cho mỗi dòng (và tạo category nếu cần)
    payloads = [build_product_payload(r, helper) for r in rows]

    # Chia thành các batch
    chunks = list(chunk_list(payloads, batch_size))
    logging.info(f"Chia thành {len(chunks)} batch, mỗi batch tối đa {batch_size} sản phẩm")

    # Gửi song song với ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(helper.batch_create_products, chunk): idx
                   for idx, chunk in enumerate(chunks)}
        for fut in as_completed(futures):
            idx = futures[fut]
            try:
                result = fut.result()
                logging.info(f"Batch #{idx} tạo thành công: {len(result.get('create', []))} sản phẩm")
            except Exception as e:
                logging.error(f"Batch #{idx} lỗi: {e}")
            # Throttle giãn cách giữa các batch để tránh spike
            time.sleep(throttle)

if __name__ == '__main__':
    import argparse

    # Thiết lập parser để chạy từ CLI
    parser = argparse.ArgumentParser(description='Feed products từ CSV qua WooCommerce batch API')
    parser.add_argument('csv_path', help='Đường dẫn file CSV đầu vào')
    parser.add_argument('--url', required=True, help='URL gốc của store')
    parser.add_argument('--ck', required=True, help='Consumer Key')
    parser.add_argument('--cs', required=True, help='Consumer Secret')
    parser.add_argument('--batch', type=int, default=80, help='Kích thước batch')
    parser.add_argument('--workers', type=int, default=3, help='Số luồng song song')
    parser.add_argument('--throttle', type=float, default=1.0, help='Giãn cách (giây) giữa các batch')
    args = parser.parse_args()

    # Gọi hàm chính
    feed_products(
        csv_path=args.csv_path,
        base_url=args.url,
        ck=args.ck,
        cs=args.cs,
        batch_size=args.batch,
        max_workers=args.workers,
        throttle=args.throttle,
    )
