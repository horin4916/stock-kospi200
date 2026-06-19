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
    
    top5_str = " | ".join([f"{row['종목명']}({row['등락률']:+.2f}%)" for _, row in top5.iterrows()])
    bottom5_str = " | ".join([f"{row['종목명']}({row['등락률']:+.2f}%)" for _, row in bottom5.iterrows()])
    
    ind_avg = df.groupby('1차 분류')['등락률'].mean().sort_values(ascending=False)
    strong_inds = ind_avg.index[0]
    weak_inds = ind_avg.index[-1]

    df_g_only = df[df['그룹사'] != '미분류']
    grp_stats = df_g_only.groupby('그룹사')['등락률'].mean() if not df_g_only.empty else None
    strong_grp = grp_stats.idxmax() if grp_stats is not None else "N/A"
    weak_grp = grp_stats.idxmin() if grp_stats is not None else "N/A"
    
    # --- Daily 대시보드와 포맷 일치 (한 줄 통합 요약 텍스트) ---
    summary_ind = (f"🏢 <b>주간 강세 산업:</b> {strong_inds} | 📉 <b>주간 소외 산업:</b> {weak_inds} | "
                   f"🚀 <b>WEEKLY TOP 5:</b> {top5_str}")

    summary_grp = (f"🤝 <b>주간 강세 그룹:</b> {strong_grp} | 📉 <b>주간 약세 그룹:</b> {weak_grp} | "
                   f"🚀 <b>WEEKLY TOP 5:</b> {top5_str}")

    # [2. 대시보드 객체 생성]
    dashboard = make_subplots(
        rows=2, cols=1,
        row_heights=[0.1, 0.9],
        vertical_spacing=0.03,
        specs=[[{"type": "xy"}], [{"type": "treemap"}]]
    )

    # [3. 트리맵 생성 - Daily와 완벽 스케일 매핑]
    fig_i = px.treemap(df, path=["1차 분류", "2차 분류", "종목명"], values="시가총액", color="등락률", 
                       custom_data=["종목_hover"], color_continuous_scale="RdBu_r", color_continuous_midpoint=0)
    
    fig_g = px.treemap(df, path=["그룹사", "종목명"], values="시가총액", color="등락률", 
                       custom_data=["종목_hover"], color_continuous_scale="RdBu_r", color_continuous_midpoint=0)

    # [4. 트레이스 추가]
    for trace in fig_i.data:
        dashboard.add_trace(trace, row=2, col=1) # Trace 0: 산업별
    for trace in fig_g.data:
        trace.visible = False
        dashboard.add_trace(trace, row=2, col=1) # Trace 1: 그룹사별

    # [5. 레이아웃 설정 - Daily 디자인 규격 완전 이식]
    dashboard.update_layout(
        template="plotly_white",
        height=1000, 
        margin=dict(t=210, b=20, l=20, r=80),
        coloraxis_colorscale="RdBu_r",
        coloraxis_cmid=0,
        
        annotations=[
            dict(text="<b>KOSPI 200 Weekly Market Map</b>", x=0, y=1.24, xref="paper", yref="paper", showarrow=False, font=dict(size=32), xanchor="left"),
            dict(text=f"분석 기간: {ref_time} | Visualization by HORIN", x=0, y=1.19, xref="paper", yref="paper", showarrow=False, font=dict(size=15, color="gray"), xanchor="left"),
            dict(text="<b>산업별 주간 트리맵 (Cap-Weighted)</b>", x=0, y=1.075, xref="paper", yref="paper", showarrow=False, font=dict(size=20), xanchor="left"),
            dict(text=summary_ind, x=0, y=1.02, xref="paper", yref="paper", showarrow=False, font=dict(size=13, color="#333"), xanchor="left", align="left")
        ],

        updatemenus=[dict(
            type="buttons", direction="left", x=0, y=1.13, xanchor="left", yanchor="top",
            active=0, showactive=True,
            buttons=[
                dict(label="🏢 산업별 주간", method="update", 
                     args=[{"visible": [True, False]}, 
                           {"annotations[2].text": "<b>산업별 주간 트리맵 (Cap-Weighted)</b>",
                            "annotations[3].text": summary_ind}]),
                dict(label="🤝 그룹사별 주간", method="update", 
                     args=[{"visible": [False, True]}, 
                           {"annotations[2].text": "<b>그룹사별 주간 트리맵 (Cap-Weighted)</b>",
                            "annotations[3].text": summary_grp}])
            ]
        )],
        
        coloraxis_colorbar=dict(
            title="주간 등락률(%)",
            thickness=20,
            lenmode="fraction", 
            len=0.90, 
            yanchor="top",
            y=0.96, 
            x=1.01,
            tickvals=[-10, -5, 0, 5, 10],
            ticktext=
