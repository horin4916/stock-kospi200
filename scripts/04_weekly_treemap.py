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

# --- [2] 데이터 로드 로직 ---
def find_latest_weekly_csv():
    files = list(DATA_WEEKLY_DIR.glob("weekly_kpi200_*.csv"))
    if not files:
        raise FileNotFoundError("주간 데이터 파일(CSV)을 찾을 수 없습니다. 전처리 스크립트를 먼저 실행하세요.")
    return max(files, key=os.path.getmtime)

def load_data(csv_file):
    df = pd.read_csv(csv_file, encoding="utf-8-sig")
    ref_time = str(df["기준시각"].iloc[0]) if not df.empty else "Weekly Period"
    
    for col in ["그룹사", "1차 분류", "2차 분류", "종목명"]:
        df[col] = df[col].fillna("미분류").astype(str).str.strip()
    
    for col in ["시가총액", "현재가", "등락률"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    
    df["등락률"] = df["등락률"].round(2)
    df["시가총액"] = df["시가총액"].astype(int)
    
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
    
    top5_str = "  |  ".join([f"{row['종목명']}({row['등락률']:+.2f}%)" for _, row in top5.iterrows()])
    bottom5_str = "  |  ".join([f"{row['종목명']}({row['등락률']:+.2f}%)" for _, row in bottom5.iterrows()])
    
    ind_avg = df.groupby('1차 분류')['등락률'].mean().sort_values(ascending=False)
    strong_inds = ", ".join(ind_avg.index[:3])
    weak_inds = ", ".join(ind_avg.index[-3:])

    # [2. 대시보드 객체 생성]
    dashboard = make_subplots(
        rows=2, cols=1,
        row_heights=[0.1, 0.9],
        vertical_spacing=0.03,
        specs=[[{"type": "xy"}], [{"type": "treemap"}]]
    )

    # [3. 트리맵 생성]
    fig_i = px.treemap(df, path=["1차 분류", "2차 분류", "종목명"], values="시가총액", color="등락률", 
                       custom_data=["종목_hover"], color_continuous_scale="RdBu_r", 
                       range_color=[-10, 10], color_continuous_midpoint=0)
    
    fig_g = px.treemap(df, path=["그룹사", "종목명"], values="시가총액", color="등락률", 
                       custom_data=["종목_hover"], color_continuous_scale="RdBu_r", 
                       range_color=[-10, 10], color_continuous_midpoint=0)

    # [4. 요약 텍스트 정의 (오류 해결 지점)]
    top_stock_name = top5.iloc[0]['종목명']
    top_stock_val = top5.iloc[0]['등락률']
    
    # 버튼 클릭 시 바뀔 텍스트들 미리 정의
    summary_ind_text = f"🏢 <b>주간 주도 산업:</b> <span style='color:red'>{strong_inds}</span>"
    summary_grp_text = f"🤝 <b>그룹사별 리포트:</b> <span style='color:red'>{top_stock_name}</span> 등락 주도"

    # [5. 트레이스 추가]
    for trace in fig_i.data:
        dashboard.add_trace(trace, row=2, col=1)
    for trace in fig_g.data:
        trace.visible = False
        dashboard.add_trace(trace, row=2, col=1)

    # [6. 레이아웃 설정]
    dashboard.update_layout(
        template="plotly_white",
        height=1100, 
        margin=dict(t=250, b=20, l=20, r=80),
        
        annotations=[
            # 인덱스 0: 메인 타이틀
            dict(text="<b>KOSPI 200 Weekly Market Map</b>", x=0, y=1.35, xref="paper", yref="paper", showarrow=False, font=dict(size=30), xanchor="left"),
            # 인덱스 1: 분석 기간
            dict(text=f"분석 기간: {ref_time} | Visualization by HORIN", x=0, y=1.29, xref="paper", yref="paper", showarrow=False, font=dict(size=14, color="gray"), xanchor="left"),
            # 인덱스 2: 산업/그룹사 요약 (버튼으로 변경될 부분)
            dict(text=summary_ind_text, x=0, y=1.20, xref="paper", yref="paper", showarrow=False, font=dict(size=15), xanchor="left"),
            # 인덱스 3: 소외 산업
            dict(text=f"📉 <b>주간 소외 산업:</b> <span style='color:blue'>{weak_inds}</span>", x=0, y=1.15, xref="paper", yref="paper", showarrow=False, font=dict(size=15), xanchor="left"),
            # 인덱스 4: TOP 5
            dict(text=f"🚀 <b>WEEKLY TOP 5:</b> {top5_str}", x=0, y=1.06, xref="paper", yref="paper", showarrow=False, font=dict(size=12, color="#d62728"), xanchor="left"),
            # 인덱스 5: BOTTOM 5
            dict(text=f"🔻 <b>WEEKLY BOTTOM 5:</b> {bottom5_str}", x=0, y=1.02, xref="paper", yref="paper", showarrow=False, font=dict(size=12, color="#1f77b4"), xanchor="left")
        ],

        updatemenus=[dict(
            type="buttons", direction="left", x=0, y=1.25, xanchor="left", yanchor="top",
            buttons=[
                dict(label="🏢 산업별 주간", method="update", 
                     args=[{"visible": [True, True, False]}, 
                           {"annotations[2].text": summary_ind_text}]),
                dict(label="🤝 그룹사별 주간", method="update", 
                     args=[{"visible": [True, False, True]}, 
                           {"annotations[2].text": summary_grp_text}])
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

    dashboard.update_traces(domain=dict(y=[0, 0.96]), row=2, col=1)
    dashboard.update_traces(hovertemplate="%{customdata[0]}<extra></extra>", row=2, col=1)

    # [7. 파일 저장]
    # ref_time에서 숫자만 추출하여 파일명 생성
    date_label = "".join(re.findall(r'\d+', ref_time.split('~')[-1]))[:8]
    if not date_label: date_label = "latest"
    
    save_path = DOCS_WEEKLY_DIR / f"weekly_dashboard_{date_label}.html"
    
    dashboard.write_html(str(save_path), include_plotlyjs="cdn", config={"displaylogo": False})

    # 최신본 복사
    shutil.copy(save_path, DOCS_DIR / "weekly_latest.html")
    
    print(f"✅ 주간 대시보드 저장 완료: {save_path.name}")
    print(f"✅ 주간 최신본 업데이트 완료: weekly_latest.html")

if __name__ == "__main__":
    make_weekly_dashboard()
