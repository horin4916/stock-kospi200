import os
import json
import re
from pathlib import Path

# 경로 설정
BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "docs"
DAILY_DIR = DOCS_DIR / "daily"

def generate_index():
    # 1. 파일 수집 (종가 리포트만)
    daily_files = sorted(list(DAILY_DIR.glob("dashboard_*_close.html")), reverse=True)
    
    daily_data = []
    for f in daily_files:
        # 파일명에서 날짜 추출 (dashboard_20260406_close.html -> 2026-04-06)
        date_match = re.search(r'(\d{4})(\d{2})(\d{2})', f.name)
        if date_match:
            date_str = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
            daily_data.append({"name": f.name, "date": date_str})

    # 2. HTML 템플릿 (CSS/JS 중괄호 이스케이프 완료)
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>KOSPI 200 Archive | HORIN</title>
        <style>
            body {{ font-family: 'Pretendard', -apple-system, sans-serif; background: #f4f6f9; color: #333; margin: 0; padding: 40px 20px; }}
            .container {{ max-width: 700px; margin: 0 auto; background: white; padding: 30px; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }}
            h1 {{ font-size: 24px; color: #1a202c; margin-bottom: 8px; text-align: center; }}
            .subtitle {{ text-align: center; color: #718096; margin-bottom: 30px; font-size: 14px; }}
            
            .filter-bar {{ display: flex; gap: 8px; margin-bottom: 25px; justify-content: center; }}
            input[type="date"] {{ border: 1px solid #e2e8f0; padding: 8px 12px; border-radius: 8px; outline: none; }}
            button {{ background: #3182ce; color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-weight: 600; }}
            button.reset {{ background: #edf2f7; color: #4a5568; }}

            ul {{ list-style: none; padding: 0; margin: 0; border-top: 1px solid #edf2f7; }}
            li {{ display: flex; justify-content: space-between; align-items: center; padding: 16px; border-bottom: 1px solid #edf2f7; transition: background 0.2s; }}
            li:hover {{ background: #f7fafc; }}
            .date-label {{ font-weight: 700; color: #2d3748; }}
            .link-btn {{ text-decoration: none; background: white; border: 1px solid #3182ce; color: #3182ce; padding: 6px 12px; border-radius: 6px; font-size: 13px; font-weight: 600; }}
            .link-btn:hover {{ background: #3182ce; color: white; }}

            .pagination {{ display: flex; justify-content: center; gap: 6px; margin-top: 30px; }}
            .page-btn {{ border: 1px solid #e2e8f0; background: white; padding: 6px 12px; border-radius: 6px; cursor: pointer; }}
            .page-btn.active {{ background: #3182ce; color: white; border-color: #3182ce; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 인베스트먼트 다이어리</h1>
            <p class="subtitle">KOSPI 200 종가 리포트 아카이브</p>

            <div class="filter-bar">
                <input type="date" id="targetDate">
                <button onclick="searchDate()">이동</button>
                <button class="reset" onclick="resetAll()">전체</button>
            </div>

            <ul id="list"></ul>
            <div id="pager" class="pagination"></div>

            <footer style="margin-top: 40px; text-align: center; font-size: 12px; color: #a0aec0;">
                마지막 업데이트: {os.popen('date').read().strip()}
            </footer>
        </div>

        <script>
            const data = {json.dumps(daily_data)};
            let currentData = [...data];
            const size = 10;
            let page = 1;

            function show(p) {{
                page = p;
                const start = (p-1) * size;
                const list = document.getElementById('list');
                list.innerHTML = '';
                
                const items = currentData.slice(start, start + size);
                if (items.length === 0) {{
                    list.innerHTML = '<li style="justify-content: center; color: #a0aec0;">리포트가 없습니다.</li>';
                }}
                
                items.forEach(d => {{
                    list.innerHTML += `<li>
                        <span class="date-label">${{d.date}}</span>
                        <a href="daily/${{d.name}}" class="link-btn">리포트 보기</a>
                    </li>`;
                }});
                drawPager();
            }}

            function drawPager() {{
                const total = Math.ceil(currentData.length / size);
                const pager = document.getElementById('pager');
                pager.innerHTML = '';
                for(let i=1; i<=total; i++) {{
                    pager.innerHTML += `<button class="page-btn ${{i===page?'active':''}}" onclick="show(${{i}})">${{i}}</button>`;
                }}
            }}

            function searchDate() {{
                const val = document.getElementById('targetDate').value;
                if(!val) return;
                currentData = data.filter(d => d.date === val);
                show(1);
            }}

            function resetAll() {{
                currentData = [...data];
                show(1);
            }}

            show(1);
        </script>
    </body>
    </html>
    """
    
    with open(DOCS_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"✅ 랜딩 페이지 생성 완료: {len(daily_data)}개의 리포트")

if __name__ == "__main__":
    generate_index()
