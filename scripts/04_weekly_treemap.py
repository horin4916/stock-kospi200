import os
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import shutil

# --- [1] 경로 및 폴더 설정 (Weekly용) ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_WEEKLY_DIR = BASE_DIR / "data" / "weekly"
DOCS_DIR = BASE_DIR / "docs"
DOCS_WEEKLY_DIR = DOCS_DIR / "weekly"

# 폴더 생성
DATA_WEEKLY_DIR.mkdir(parents=True, exist_ok=True)
DOCS_WEEKLY_DIR.mkdir(parents=True, exist_ok=True)

# --- [2] 최신 주간 데이터 로드 로직 ---
def find_latest_weekly_csv():
    # weekly_summary 스크립트가 만든 파일들 탐색
    files = list(DATA_WEEKLY_DIR.glob("weekly_kpi200_*.csv"))
    if not files:
        raise FileNotFoundError("주간 데이터 파일(CSV)을 찾을 수 없습니다. 전처리 스크립트를 먼저 실행하세요.")
    # 가장 최근 수정된 파일 반환
    return max(files, key=os.path.getmtime)

def load_data(csv_file):
    df = pd.read_csv(csv_file, encoding="utf-8-sig")
    # 전처리 단계에서 주입한 '03.20~03.27 Weekly' 형태의 라벨 활용
    ref_time = str(df["기준시각"].iloc[0]) if not df.empty else "Weekly"
    
    for col in ["그룹사", "1차 분류", "2차 분류", "종목명"]:
        df[col] = df[col].fillna("미분류").astype(str).str.strip()
    
    # 숫자형 변환
    for col in ["시가총액", "현재가", "등락률"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    
    df["시가총액"] = df["시가총액"].astype(int)
    
    # 호버 텍스트 (주간 등락률 명시)
    df["종목_hover"] = df.apply(lambda r: 
        f"<b>{r['종목명']} ({r['그룹사']})</b><br>"
        f"시가총액: {r['시가총액']:,}억<br>"
        f"현재가: {r['현재가']:,}원<br>"
        f"<b>주간 등락: {r['등락률']:+.2f}%</b>", axis=1)
    
    return df, ref_time

# --- [3] 메인 실행 함수 ---
def make_weekly_dashboard():
    try:
        csv_file = find_latest_weekly_csv()
        df, ref_time = load_data(csv_file)
    except Exception as e:
        print(f"❌ Error loading weekly data: {e}")
        return

    # [데이터 계산]
    top5 = df.nlargest(5, '등락률')
    bottom5 = df.nsmallest(5, '등락률')
    
    # 텍스트 포맷팅 (예: 삼성전자(+2.5%) / SK하이닉스(+1.2%))
    top5_str = "  |  ".join([f"{row['종목명']}({row['등락률']:+.2f}%)" for _, row in top5.iterrows()])
    bottom5_str = "  |  ".join([f"{row['종목명']}({row['등락률']:+.2f}%)" for _, row in bottom5.iterrows()])
    
    # 산업별 평균 계산 및 정렬
    ind_avg = df.groupby('1차 분류')['등락률'].mean().sort_values(ascending=False)
    strong_inds = ", ".join(ind_avg.index[:3])  # 상위 3개 산업
    weak_inds = ", ".join(ind_avg.index[-3:])   # 하위 3개 산업

    # [2. 대시보드 객체 생성]
    dashboard = make_subplots(
        rows=2, cols=1,
        row_heights=[0.1, 0.9],
        vertical_spacing=0.03,
        specs=[[{"type": "xy"}], [{"type": "treemap"}]]
    )

    # [3. 트리맵 생성 (주간 변동성에 맞춰 컬러 범위 ±10%로 확장)]
    fig_i = px.treemap(df, path=["1차 분류", "2차 분류", "종목명"], values="시가총액", color="등락률", 
                       custom_data=["종목_hover"], color_continuous_scale="RdBu_r", 
                       range_color=[-10, 10], color_continuous_midpoint=0)
    
    fig_g = px.treemap(df, path=["그룹사", "종목명"], values="시가총액", color="등락률", 
                       custom_data=["종목_hover"], color_continuous_scale="RdBu_r", 
                       range_color=[-10, 10], color_continuous_midpoint=0)

    # [4. 요약 텍스트 구성]
    summary_ind = (f"📈 <b>주간 강세 산업:</b> {strong_1st} | 📉 <b>약세:</b> {weak_1st} | "
                   f"🚀 <b>Top:</b> {top_stock['종목명']}({top_stock['등락률']:+.2f}%)")

    summary_grp = (f"📈 <b>주간 강세 그룹:</b> {strong_grp} | 📉 <b>약세:</b> {weak_grp} | "
                   f"🚀 <b>Top:</b> {top_stock['종목명']}({top_stock['등락률']:+.2f}%)")

    # [5. 트레이스 추가]
    for trace in fig_i.data:
        dashboard.add_trace(trace, row=2, col=1)
    for trace in fig_g.data:
        trace.visible = False
        dashboard.add_trace(trace, row=2, col=1)

    # [6. 레이아웃 및 컬러바 최적화]
    dashboard.update_layout(
        template="plotly_white",
        height=1000, 
        margin=dict(t=210, b=20, l=20, r=80),
        
        annotations=[
            # [Level 1] 메인 타이틀 및 기간
            dict(text="<b>KOSPI 200 Weekly Market Map</b>", x=0, y=1.35, xref="paper", yref="paper", showarrow=False, font=dict(size=30), xanchor="left"),
            dict(text=f"분석 기간: {ref_time} | Visualization by HORIN", x=0, y=1.29, xref="paper", yref="paper", showarrow=False, font=dict(size=14, color="gray"), xanchor="left"),
        
            # [Level 2] 섹터 요약 (강세/약세 산업)
            dict(text=f"🏢 <b>주간 주도 산업:</b> <span style='color:red'>{strong_inds}</span>", x=0, y=1.20, xref="paper", yref="paper", showarrow=False, font=dict(size=15), xanchor="left"),
            dict(text=f"📉 <b>주간 소외 산업:</b> <span style='color:blue'>{weak_inds}</span>", x=0, y=1.15, xref="paper", yref="paper", showarrow=False, font=dict(size=15), xanchor="left"),
        
            # [Level 3] 종목 랭킹 (상/하위 5종목) - 트리맵 바로 위에 배치
            dict(text=f"🚀 <b>WEEKLY TOP 5:</b> {top5_str}", x=0, y=1.06, xref="paper", yref="paper", showarrow=False, font=dict(size=12, color="#d62728"), xanchor="left"),
            dict(text=f"🔻 <b>WEEKLY BOTTOM 5:</b> {bottom5_str}", x=0, y=1.02, xref="paper", yref="paper", showarrow=False, font=dict(size=12, color="#1f77b4"), xanchor="left")
        ],

        updatemenus=[dict(
            type="buttons", direction="left", x=0, y=1.13, xanchor="left", yanchor="top",
            buttons=[
                dict(label="🏢 산업별 주간", method="update", 
                     args=[{"visible": [True, True, False]}, 
                           {"annotations[2].text": "<b>산업별 주간 등락 리포트</b>", "annotations[3].text": summary_ind}]),
                dict(label="🤝 그룹사별 주간", method="update", 
                     args=[{"visible": [True, False, True]}, 
                           {"annotations[2].text": "<b>그룹사별 주간 등락 리포트</b>", "annotations[3].text": summary_grp}])
            ]
        )],
        
        coloraxis_colorbar=dict(
            title="주간 등락률(%)",
            thickness=20,
            lenmode="fraction", len=0.76, 
            yanchor="top", y=0.96, x=1.01,
            tickvals=[-10, -5, 0, 5, 10],
            ticktext=["-10%", "-5%", "0%", "+5%", "+10%"]
        )
    )

    # [7. 트리맵 영역 및 호버 설정]
    dashboard.update_traces(domain=dict(y=[0, 0.96]), row=2, col=1)
    dashboard.update_traces(hovertemplate="%{customdata[0]}<extra></extra>", row=2, col=1)

    # [8. 파일 저장]
    # 파일명에서 날짜 추출 (예: 03.20~03.27 -> 0327)
    date_label = re.sub(r'[^0-9]', '', ref_time.split('~')[-1])[:4]
    save_path = DOCS_WEEKLY_DIR / f"weekly_dashboard_{date_label}.html"
    
    dashboard.write_html(str(save_path), include_plotlyjs="cdn", config={"displaylogo": False})
    # 최신 파일 복사
    shutil.copy(save_path, DOCS_DIR / "weekly_latest.html")
    
    print(f"✅ 주간 대시보드 저장 완료: {save_path.name}")

if __name__ == "__main__":
    make_weekly_dashboard()
