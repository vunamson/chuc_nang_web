import sys
from hide_products import hide_products
from domain_check import run as check_domains
from delete_product import run_delete
from feed_product import feed_products  # Nhúng module feed sản phẩm



def main():
    print("=== QUẢN LÝ SHOP AUTOMATION ===")
    print("1. Ẩn sản phẩm theo category")
    print("2. Xóa sản phẩm theo yêu cầu")
    print("3. Feed sản phẩm từ file CSV")
    print("4. Kiểm tra domain (tuổi & giá)")
    api_url = 'https://hartca.com'
    ck      = 'ck_e6339b1b9b988258eb0faa7cef2a7adf03a55f5f'
    cs      = 'cs_a4ff2993fb69780aa08f15db40e78b7eaeee959b'
    categories  = [171,128,1726,140,1728,1724,1722,138,135,1723,270]
    max_workers = 10

    choice = input("Chọn chức năng (1-4): ").strip()
    
    if choice == "1":
        for cat_id in categories :
            hide_products(
                category_id=cat_id,
                base_url=api_url,
                consumer_key=ck,
                consumer_secret=cs,
                max_workers = max_workers,
            )
    elif choice == "4":
        # Chạy trình kiểm tra domain tuổi và giá
        check_domains()
    elif choice == "2":
        run_delete(api_url, ck, cs, max_workers)
    elif choice == "3":
        # Feed sản phẩm từ file CSV
        # 1) Nhập đường dẫn file CSV từ người dùng
        csv_path = input("Nhập đường dẫn tới file CSV: ").strip()
        # 2) Gọi hàm feed_products đã cài ở feed_product.py
        #    Tham số: đường dẫn CSV, URL store, key/secret, batch_size, workers, throttle
        feed_products(
            csv_path=csv_path,
            base_url=api_url,
            ck=ck,
            cs=cs,
            batch_size=80,    # số sản phẩm gửi 1 batch
            max_workers=3,    # số batch chạy song song
            throttle=1.0      # giãn cách (giây) giữa các batch
        )
    else:
        print("❗ Lựa chọn không hợp lệ. Vui lòng chạy lại và chọn 1-4.")

if __name__ == "__main__":
    main()
