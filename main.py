import sys
from hide_products import hide_products
from domain_check import run as check_domains
from delete_product import run_delete


def main():
    print("=== QUẢN LÝ SHOP AUTOMATION ===")
    print("1. Ẩn sản phẩm theo category")
    print("2. Xóa sản phẩm theo yêu cầu")
    print("3. Tính năng 3 (chưa có)")
    print("4. Kiểm tra domain (tuổi & giá)")
    api_url = 'https://bokocoko.com'
    ck      = 'ck_eddf9ccb7607fe7978e0fcbf27982e4d68ed84b0'
    cs      = 'cs_67c736aaf25e2e1488e266ad0167fdcf5372c759'
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
    elif choice in {"2", "3"}:
        print(f"⚙ Tính năng {choice} đang được phát triển…")
    elif choice == "2":
        run_delete(api_url, ck, cs, max_workers)
    else:
        print("❗ Lựa chọn không hợp lệ. Vui lòng chạy lại và chọn 1-4.")

if __name__ == "__main__":
    main()
