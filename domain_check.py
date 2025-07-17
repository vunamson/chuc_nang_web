import csv
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import whois


def get_domain_age(domain):
    """Trả về tuổi domain (năm), hoặc None nếu không tra được"""
    print ('domain' ,domain)
    try:
        # w = whois.whois(domain)
        try:
            w = whois.whois(domain)
        except Exception as e:
            print(f"✖ Lỗi khi gọi whois.whois({domain}): {e}")
            return None
        created = w.creation_date
        if isinstance(created, list):
            created = created[0]
        if not created:
            return None
        age = (datetime.now() - created).days / 365.25
        return round(age, 2)
    except Exception:
        return None


def load_domains_from_csv(path, domain_col, price_col='price'):
    """Đọc file CSV và trả về list các dict: {'domain': ..., 'price': ...} """
    domains = []
    try:
        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                d = row.get(domain_col, '').strip()
                p = row.get(price_col, '').strip()
                try:
                    price = float(p)
                except:
                    continue
                if d:
                    domains.append({'domain': d, 'price': price})
    except FileNotFoundError:
        print(f"Không tìm thấy file: {path}")
    return domains


def filter_domains(domains, min_age, max_price, max_workers=3):
    """Lọc các domain thỏa mãn tuổi >= min_age và giá <= max_price"""
    results = []
    com_domains = [d for d in domains if d['domain'].lower().endswith('.com') and d['price'] <= max_price]
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_dom = {executor.submit(get_domain_age, d['domain']): d for d in com_domains}
        for future in as_completed(future_to_dom):
            dom = future_to_dom[future]
            age = future.result()
            if age is not None and age >= min_age and dom['price'] <= max_price:
                results.append({'domain': dom['domain'], 'age': age, 'price': dom['price']})
                print('ℹ️ domain thỏa mãn yêu cầu' , {dom['domain']})
    return results


def run():
    print("=== DOMAIN AGE & PRICE CHECKER ===")
    print("1. Check Auctions file")
    print("2. Check Buy Now file")
    choice = input("Chọn tệp (1-2): ").strip()
    domain_col = ''
    if choice == '1':
        domain_col = 'name'
        path = input("Nhập đường dẫn Auctions CSV: ").strip()
    elif choice == '2':
        domain_col = 'domain'
        path = input("Nhập đường dẫn Buy Now CSV: ").strip()
    else:
        print("Lựa chọn không hợp lệ.")
        return

    try:
        min_age = float(input("Nhập tuổi domain tối thiểu (năm): ").strip())
        max_price = float(input("Nhập giá tối đa (USD): ").strip())
    except ValueError:
        print("Tuổi hoặc giá không hợp lệ.")
        return

    domains = load_domains_from_csv(path,domain_col)
    print(f"\nĐang kiểm tra {len(domains)} domain...\n")
    results = filter_domains(domains, min_age, max_price)
    output_file = input("list_domain_check.csv").strip() or "output.csv"
    if not results:
        print("Không tìm thấy domain nào thỏa mãn điều kiện.")
    else:
        print(f"\nDanh sách domain >={min_age} năm & <=${max_price}:\n")
        for r in results:
            print(f"- {r['domain']} | Age: {r['age']} năm | Price: ${r['price']}")
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['domain', 'age', 'price'])
            writer.writeheader()
            writer.writerows(results)
        print(f"✅ Đã lưu {len(results)} domain thỏa mãn vào file: {output_file}")
    except Exception as e:
        print(f"✖ Lỗi khi lưu file: {e}")

if __name__ == '__main__':
    run()
