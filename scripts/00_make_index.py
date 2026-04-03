import os
from pathlib import Path
import re

# 경로 설정
BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "docs"
DAILY_DIR = DOCS_DIR / "daily"
WEEKLY_DIR = DOCS_DIR / "weekly"

def generate_index():
    # 1. 파일 수집
    # 종가(_close) 파일만 가져옵니다. (장중 파일은 인덱스에서 제외)
    daily_files = sorted(list(DAILY_DIR.glob("*_close.html")), reverse=True)
    weekly_files = sorted(list(WEEKLY_DIR.glob("*.html")), reverse=True)

    # 2. HTML 템플릿 생성
    # 팁: f.name[10:20] 대신 파일명에서 날짜를 예쁘게 뽑는 로직을 적용했습니다.
    daily_list_items = []
    for f in daily_files:
        # 파일명(dashboard_20260403_close.html)에서 날짜 추출
        date_match = re.search(r'(\d{4})(\d{2})(\d{2})', f.name)
        date_display = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}" if date_match else f.name
        
        item = f"<li><a href='daily/{f.name}'>{date_display} 종가 리포트</a></li>"
        daily_list_items.append(item)

    weekly_list_items = [f"<li><a href='weekly/{f.name}'>{f.name}</a></li>" for f in weekly_files]

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>KOSPI 200 Dashboard Index</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #333; }}
            h1 {{ border-bottom: 3px solid #007bff; padding-bottom: 10px; }}
            .section {{ margin-bottom: 40px; }}
            h2 {{ color: #555; }}
            ul {{ list-style: none; padding: 0; }}
            li {{ margin: 12px 0; border: 1px solid #eee; padding: 15px; border-radius: 8px; transition: 0.2s; }}
            li:hover {{ background: #f8f9fa; border-color: #007bff; }}
            a {{ text-decoration: none; color: #007bff; font-weight: bold; font-size: 1.1em; }}
        </style>
    </head>
    <body>
        <h1>📊 마켓 대시보드 리포트 보관함</h1>
        
        <div class="section">
            <h2>📅 주간 리포트 (Weekly)</h2>
            <ul>
                {"".join(weekly_list_items) if weekly_list_items else "<li>아직 리포트가 없습니다.</li>"}
            </ul>
        </div>

        <div class="section">
            <h2>🕒 일간 종가 리포트 (Daily Final)</h2>
            <ul>
                {"".join(daily_list_items) if daily_list_items else "<li>아직 리포트가 없습니다.</li>"}
            </ul>
        </div>
        
        <footer style="margin-top: 50px; color: #aaa; font-size: 0.8em; text-align: center;">
            Last updated: {os.popen('date').read()}
        </footer>
    </body>
    </html>
    """

    # 3. index.html 저장
    with open(DOCS_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"✅ Index 페이지 갱신 완료 (일간 {len(daily_files)}건, 주간 {len(weekly_files)}건)")

if __name__ == "__main__":
    generate_index()
