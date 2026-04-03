import os
from pathlib import Path
import re

# 경로 설정
BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "docs"
DAILY_DIR = DOCS_DIR / "daily"
WEEKLY_DIR = DOCS_DIR / "weekly"

def generate_index():
    # '_close'가 포함된 파일만 찾아서 날짜순 정렬
    daily_files = sorted(list(DAILY_DIR.glob("*_close.html")), reverse=True)
    weekly_files = sorted(list(WEEKLY_DIR.glob("*.html")), reverse=True)
    
       
    # 2. [핵심] 종가 파일만 필터링 (예: 15시 30분 이후 생성된 파일)
    # 파일명 예시: dashboard_202604011540.html (15시 40분 파일)
    daily_final_files = []
    
    # 날짜별로 그룹화하여 가장 마지막 시간대 파일만 선택하는 로직
    date_map = {}
    for f in all_daily_files:
        # 파일명에서 날짜(8자리)와 시간(4자리) 추출
        match = re.search(r'dashboard_(\d{8})(\d{4})', f.name)
        if match:
            date, time = match.groups()
            # 1530(오후 3시 30분) 이후 파일만 후보로 등록
            if int(time) >= 1530:
                if date not in date_map or int(time) > int(date_map[date][0]):
                    date_map[date] = (time, f)

    # 필터링된 파일들만 리스트에 담고 최신순 정렬
    daily_files = sorted([val[1] for val in date_map.values()], key=lambda x: x.name, reverse=True)
    
    # 주간 파일은 그대로 가져오기
    weekly_files = sorted(list(WEEKLY_DIR.glob("*.html")), reverse=True)

    # 2. HTML 템플릿 생성
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>KOSPI 200 Dashboard Index</title>
        <style>
            body {{ font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 0 20px; }}
            h1 {{ border-bottom: 2px solid #333; padding-bottom: 10px; }}
            .section {{ margin-bottom: 30px; }}
            ul {{ list-style: none; padding: 0; }}
            li {{ margin: 10px 0; border: 1px solid #eee; padding: 10px; border-radius: 5px; }}
            li:hover {{ background: #f9f9f9; }}
            a {{ text-decoration: none; color: #007bff; font-weight: bold; }}
            .date {{ color: #666; font-size: 0.9em; margin-left: 10px; }}
        </style>
    </head>
    <body>
        <h1>📊 마켓 대시보드 리포트 보관함</h1>
        
        <div class="section">
            <h2>📅 주간 리포트 (Weekly)</h2>
            <ul>
                {"".join([f"<li><a href='weekly/{f.name}'>{f.name}</a></li>" for f in weekly_files])}
            </ul>
        </div>

        <div class="section">
            <h2>🕒 일간/시간별 리포트 (Daily)</h2>
            <ul>
                {"".join([f"<li><a href='daily/{f.name}'>{f.name}</a><span class='date'>{f.name[10:20]}</span></li>" for f in daily_files])}
            </ul>
        </div>
    </body>
    </html>
    """

    # 3. index.html 저장
    with open(DOCS_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print("✅ Index 페이지가 생성되었습니다: docs/index.html")

if __name__ == "__main__":
    generate_index()
