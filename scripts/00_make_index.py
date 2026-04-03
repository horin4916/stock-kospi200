import os
from pathlib import Path

# 경로 설정
BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "docs"
DAILY_DIR = DOCS_DIR / "daily"
WEEKLY_DIR = DOCS_DIR / "weekly"

def generate_index():
    # 1. 파일 목록 가져오기 및 정렬 (최신순)
    daily_files = sorted(list(DAILY_DIR.glob("*.html")), reverse=True)
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
