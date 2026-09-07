import os
import time
import datetime
import requests
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def get_google_sheet():
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    # credentials.json 파일에서 인증 정보를 로드
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    # 구글 시트 파일 이름
    sheet = client.open('PC부품_가격추적').sheet1
    return sheet

def fetch_compuzone(keyword):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
    }
    url = f"https://www.compuzone.co.kr/search/search.htm?searched_item={keyword}"
    
    results = []
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        products = soup.select('ul.product_list > li')
        count = 0
        for product in products:
            name_elem = product.select_one('.prd_name')
            price_elem = product.select_one('.price')
            
            if name_elem and price_elem:
                name = name_elem.text.strip()
                price_str = price_elem.text.strip().replace(',', '').replace('원', '')
                try:
                    price = int(price_str)
                except ValueError:
                    price = price_str
                    
                results.append(('컴퓨존', name, price))
                count += 1
                if count >= 2:  # 키워드당 상위 2개 수집
                    break
    except Exception as e:
        print(f"[에러] {keyword}: {e}")
        
    return results

def run():
    now = datetime.datetime.now()
    today_date = now.strftime('%Y-%m-%d')
    current_time = now.strftime('%H:%M:%S')
    
    print("컴퓨존 가격 수집 시작...")
    target_keywords = ["라이젠 5600", "RTX 5060"]
    rows_to_append = []
    
    for kw in target_keywords:
        data = fetch_compuzone(kw)
        for shop, name, price in data:
            rows_to_append.append([today_date, current_time, shop, name, price])
        time.sleep(2)
        
    if rows_to_append:
        sheet = get_google_sheet()
        if not sheet.get_all_values():
            sheet.append_row(["수집일자", "수집시간", "쇼핑몰", "상품명", "가격(원)"])
        sheet.append_rows(rows_to_append)
        print("구글 시트 저장 완료!")

if __name__ == "__main__":
    run()