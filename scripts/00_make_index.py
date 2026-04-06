import os
from pathlib import Path
import re
import json

# 경로 설정
BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "docs"
DAILY_DIR = DOCS_DIR / "daily"
WEEKLY_DIR = DOCS_DIR / "weekly"

def generate_index():
    # 1. 데이터 수집 및 구조화
    daily_files = sorted(list(DAILY_DIR.glob("*_close.html")), reverse=True)
    weekly_files = sorted(list(WEEKLY_DIR.glob("*.html")), reverse=True)

    # 자바스크립트에서 쓸 수 있게 데이터 리스트 생성
    daily_data = []
    for f in daily_files:
        date_match = re.search(r'(\d{4})(\d{2})(\d{2})', f.name)
        date_str = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}" if date_match else "unknown"
        daily_data.append({"name": f.name, "date": date_str, "type": "daily"})

    weekly_data = [{"name": f.name, "date": f.name[:10], "type": "weekly"} for f in weekly_files]

    # 2. HTML 템플릿 생성 (f-string 내 중괄호는 {{ }} 로 이스케이프 처리)
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>HORIN's Market Dashboard</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #333; background: #f9f9f9; }}
            .container {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
            h1 {{ border-bottom: 3px solid #007bff; padding-bottom: 10px; text-align: center; color: #2c3e50; }}
            
            .controls {{ display: flex; gap: 10px; margin: 20px 0; justify-content: center; flex-wrap: wrap; }}
            input[type="date"], button {{ padding: 10px 15px; border-radius: 6px; border: 1px solid #ddd; font-size: 14px; }}
            button {{ background: #007bff; color: white; border: none; cursor: pointer; transition: 0.2s; }}
            button:hover {{ background: #0056b3; }}
            button.secondary {{ background: #6c757d; }}

            ul {{ list-style: none; padding: 0; min-height: 400px; }}
            li {{ margin: 10px 0; border: 1px solid #eee; padding: 15px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; background: white; }}
            .report-date {{ font-weight: bold; color: #555; }}
            .btn-open {{ text-decoration: none; color: #007bff; font-weight: bold; border: 1px solid #007bff; padding: 5px 12px; border-radius: 4px; }}
            .btn-open:hover {{ background: #007bff; color: white; }}

            .pagination {{ display: flex; justify-content: center; gap: 5px; margin-top: 20px; }}
            .page-link {{ padding: 8px 12px; border: 1px solid #ddd; background: white; cursor: pointer; border-radius: 4px; }}
            .page-link.active {{ background: #007bff; color: white; border-color: #007bff; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 마켓 대시보드 리포트 보관함</h1>
            
            <div class="controls">
                <input type="date" id="datePicker">
                <button onclick="filterByDate()">날짜 이동</button>
                <button class="secondary" onclick="resetFilter()">전체 보기</button>
            </div>

            <div id="listContainer">
                <h2 id="viewTitle">📅 일간 종가 리포트</h2>
                <ul id="reportList"></ul>
            </div>

            <div id="pagination" class="pagination"></div>

            <footer style="margin-top: 50px; color: #aaa; font-size: 0.8em; text-align: center;">
                Last updated: {os.popen('date').read().strip()} | Visualization by HORIN
            </footer>
        </div>

        <script>
            const dailyData = {json.dumps(daily_data)};
            const itemsPerPage = 10;
            let filteredData = [...dailyData];
            let currentPage = 1;

            function renderList(page) {{
                const start = (page - 1) * itemsPerPage;
                const end = start + itemsPerPage;
                const listEl = document.getElementById('reportList');
                listEl.innerHTML = '';

                const pagedItems = filteredData.slice(start, end);
                if (pagedItems.length === 0) {{
                    listEl.innerHTML = '<li style="justify-content:center;">해당 조건의 리포트가 없습니다.</li>';
                }}

                pagedItems.forEach(item => {{
                    listEl.innerHTML += `<li>
                        <span class="report-date">${{item.date}} 종가 리포트</span>
                        <a href="daily/${{item.name}}" class="btn-open">리포트 열기</a>
                    </li>`;
                }});
                renderPagination();
            }}

            function renderPagination() {{
                const totalPages = Math.ceil(filteredData.length / itemsPerPage);
                const pagEl = document.getElementById('pagination');
                pagEl.innerHTML = '';

                for (let i = 1; i <= totalPages; i++) {{
                    pagEl.innerHTML += `<button class="page-link ${{i === currentPage ? 'active' : ''}}" 
                                        onclick="goToPage(${{i}})">${{i}}</button>`;
                }}
            }}

            function goToPage(page) {{
                currentPage = page;
                renderList(page);
                window.scrollTo(0, 0);
            }}

            function filterByDate() {{
                const selectedDate = document.getElementById('datePicker').value;
                if (!selectedDate) return;
                filteredData = dailyData.filter(d => d.date === selectedDate);
                currentPage = 1;
                renderList(1);
            }}

            function resetFilter() {{
                filteredData = [...dailyData];
                currentPage = 1;
                renderList(1);
            }}

            // 초기 실행
            renderList(1);
        </script>
    </body>
    </html>
    """
