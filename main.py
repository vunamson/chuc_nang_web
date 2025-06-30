import sys
from hide_products import hide_products

def main():
    print("=== QUẢN LÝ SHOP AUTOMATION ===")
    print("1. Ẩn sản phẩm theo category")
    print("2. Tính năng 2 (chưa có)")
    print("3. Tính năng 3 (chưa có)")
    print("4. Tính năng 4 (chưa có)\n")
    api_url = 'https://lacadella.com'
    ck      = 'ck_c3e45e1dbee2160c2bf7fb77d8a12b3a43a15411'
    cs      = 'cs_3f8568a84aceb7bf864dd4c34ad99c349fb9ca70'
    cat_id  = 155
    max_workers = 30

    choice = input("Chọn chức năng (1-4): ").strip()
    
    if choice == "1":
        hide_products(
            category_id=cat_id,
            base_url=api_url,
            consumer_key=ck,
            consumer_secret=cs,
            max_workers = max_workers,
        )

    elif choice in {"2", "3", "4"}:
        print(f"⚙ Tính năng {choice} đang được phát triển…")
    else:
        print("❗ Lựa chọn không hợp lệ. Vui lòng chạy lại và chọn 1-4.")

if __name__ == "__main__":
    main()
