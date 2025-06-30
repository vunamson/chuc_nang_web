# File: hide_products.py
import requests
from requests.auth import HTTPBasicAuth
from concurrent.futures import ThreadPoolExecutor, as_completed



def _hide_one_product(prod_id: int, api_base: str, auth: HTTPBasicAuth) -> str:
    """
    Helper: ẩn 1 sản phẩm qua REST API, trả về thông điệp kết quả.
    """
    update_url = f"{api_base}/products/{prod_id}"
    payload = {
        "catalog_visibility": "hidden",
        "meta_data": [{"key": "_hwp_hide_product", "value": "yes"}]
    }
    r = requests.put(update_url, json=payload, auth=auth)
    if r.status_code == 200:
        return f"✔ Hid product ID {prod_id}"
    else:
        return f"✖ Failed to hide product ID {prod_id}: {r.status_code}"

def hide_products(category_id: int,
                  base_url: str,
                  consumer_key: str,
                  consumer_secret: str,
                  per_page: int = 100,
                  max_workers: int = 5) -> None:
    """
    Hide all products in a WooCommerce category by:
      - Setting 'catalog_visibility' to 'hidden' (excludes from shop, search, archives)
      - (Optionally) Marking custom meta '_hwp_hide_product' = 'yes' for compatibility

    Args:
        category_id: ID of the product category.
        base_url: Base site URL, e.g. 'https://your-shop.com' (no trailing slash).
        consumer_key: WooCommerce REST API Consumer Key.
        consumer_secret: WooCommerce REST API Consumer Secret.
        per_page: Number of products per page (max 100).
    """
    auth = HTTPBasicAuth(consumer_key, consumer_secret)
    api_base = base_url.rstrip('/') + '/wp-json/wc/v3'
    page = 1
    while True:
        # Fetch products in the category
        list_url = f"{api_base}/products"
        resp = requests.get(
            list_url,
            params={"category": category_id, "per_page": per_page, "page": page},
            auth=auth
        )
        resp.raise_for_status()
        products = resp.json()
        if not products:
            print("✅ All products hidden.")
            break

         # 2) Lọc chỉ những sản phẩm CHƯA ẩn
        to_hide = []
        for p in products:
            # nếu đã ẩn qua catalog_visibility thì bỏ qua
            if p.get("catalog_visibility") == "hidden":
                continue
            # nếu đã có meta _hwp_hide_product = yes thì bỏ qua
            for m in p.get("meta_data", []):
                if m.get("key") == "_hwp_hide_product" and m.get("value") == "yes":
                    break
            else:
                # không break => chưa có meta, thêm vào danh sách xử lý
                to_hide.append(p)

        if not to_hide:
            print(f"ℹ️  Page {page}: không có sản phẩm mới cần ẩn.")
            page += 1
            continue


        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # submit tất cả các job
            futures = {
                executor.submit(_hide_one_product, p["id"], api_base, auth): p["id"]
                for p in to_hide  if "id" in p
            }
            # in kết quả khi từng job hoàn thành
            for fut in as_completed(futures):
                print(fut.result())

        page += 1
