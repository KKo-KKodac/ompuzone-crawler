import os
import time
import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def get_google_sheet():
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open('PC부품_가격추적').sheet1
    return sheet

def fetch_compuzone(keyword):
    # 세션 생성 및 재시도 설정 (연결 불안정 대비)
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # 헤더 보완 (더 실제 브라우저와 유사하게 설정)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive'
    }
    
    url = f"https://www.compuzone.co.kr/search/search.htm?searched_item={keyword}"
    results = []
    
    try:
        # 타임아웃을 20초로 여유있게 설정
        res = session.get(url, headers=headers, timeout=20)
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
                if count >= 2:
                    break
    except Exception as e:
        print(f"[컴퓨존 수집 에러 - {keyword}] {e}")
        
    return results

def run():
    now = datetime.datetime.now()
    today_date = now.strftime('%Y-%m-%d')
    current_time = now.strftime('%H:%M:%S')
    
    print("=== 컴퓨존 가격 수집 시작 ===")
    target_keywords = ["라이젠 5600", "RTX 5060"]
    rows_to_append = []
    
    for kw in target_keywords:
        data = fetch_compuzone(kw)
        print(f"'{kw}' 수집 결과: {len(data)}개 항목 수집")
        for shop, name, price in data:
            rows_to_append.append([today_date, current_time, shop, name, price])
        time.sleep(3)
        
    if rows_to_append:
        try:
            print("구글 시트에 수집 결과 기록 중...")
            sheet = get_google_sheet()
            if not sheet.get_all_values():
                sheet.append_row(["수집일자", "수집시간", "쇼핑몰", "상품명", "가격(원)"])
            sheet.append_rows(rows_to_append)
            print(f" 성공: {len(rows_to_append)}개 항목이 구글 시트에 기록되었습니다!")
        except Exception as e:
            print(f"❌ [구글 시트 저장 에러] {e}")
            raise e
    else:
        print("❌ 데이터 수집에 실패했습니다 (접근 차단 또는 타임아웃 발생).")
        raise Exception("컴퓨존 데이터 수집 실패")

if __name__ == "__main__":
    run()
