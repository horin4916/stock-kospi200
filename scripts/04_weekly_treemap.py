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
    strong_inds = ", ".join(ind_avg.index[:3])
    weak_inds = ", ".join(ind_avg.index[-3:])

    df_g_only = df[df['그룹사'] != '미분류']
    grp_stats = df_g_only.groupby('그룹사')['등락률'].mean().sort_values(ascending=False) if not df_g_only.empty else None
    strong_grp = ", ".join(grp_stats.index[:3]) if grp_stats is not None else "N/A"
    weak_grp = ", ".join(grp_stats.index[-3:]) if grp_stats is not None else "N/A"
    
    # 🌟 [기존 방식 유지] 기존 이미지의 다채로운 개별 리포트 텍스트 복원
    summary_ind_lead = f"🏢 <b>주간 주도 산업:</b> <span style='color:#d62728'>{strong_inds}</span>"
    summary_ind_lag  = f"📉 <b>주간 소외 산업:</b> <span style='color:#1f77b4'>{weak_inds}</span>"

    summary_grp_lead = f"🤝 <b>주간 강세 그룹:</b> <span style='color:#d62728'>{strong_grp}</span>"
    summary_grp_lag  = f"📉 <b>주간 약세 그룹:</b> <span style='color:#1f77b4'>{weak_grp}</span>"

    # [2. 대시보드 객체 생성]
    dashboard = make_subplots(
        rows=2, cols=1,
        row_heights=[0.08, 0.92], # 상단 요약문 확보를 위해 본체 비율 소폭 조정
        vertical_spacing=0.03,
        specs=[[{"type": "xy"}], [{"type": "treemap"}]]
    )

    # [3. 트리맵 생성]
    fig_i = px.treemap(df, path=["1차 분류", "2차 분류", "종목명"], values="시가총액", color="등락률", 
                       custom_data=["종목_hover"], color_continuous_scale="RdBu_r", range_color=[-10, 10], color_continuous_midpoint=0)
    
    fig_g = px.treemap(df, path=["그룹사", "종목명"], values="시가총액", color="등락률", 
                       custom_data=["종목_hover"], color_continuous_scale="RdBu_r", range_color=[-10, 10], color_continuous_midpoint=0)

    # [4. 트레이스 추가]
    for trace in fig_i.data:
        dashboard.add_trace(trace, row=2, col=1) # Trace 0: 산업별
    for trace in fig_g.data:
        trace.visible = False
        dashboard.add_trace(trace, row=2, col=1) # Trace 1: 그룹사별

    # [5. 레이아웃 설정 - 상단은 신규(Daily) 형태, 하단 요약은 기존(Weekly) 4줄 분리 구조 융합]
    dashboard.update_layout(
        template="plotly_white",
        height=1100, # 요약문 4줄 분리 처리를 위해 높이 증대
        margin=dict(t=240, b=20, l=20, r=80), # 상단 여백 확대
        coloraxis_colorscale="RdBu_r",
        coloraxis_cmid=0,
        
        annotations=[
            # 인덱스 0: 신규 대형 타이틀 적용
            dict(text="<b>KOSPI 200 Weekly Market Map</b>", x=0, y=1.26, xref="paper", yref="paper", showarrow=False, font=dict(size=32), xanchor="left"),
            # 인덱스 1: 신규 서브 타이틀 정보
            dict(text=f"분석 기간: {ref_time} | Visualization by HORIN", x=0, y=1.21, xref="paper", yref="paper", showarrow=False, font=dict(size=15, color="gray"), xanchor="left"),
            
            # 인덱스 2: 주도 산업 / 강세 그룹 (버튼 클릭 시 교체됨)
            dict(text=summary_ind_lead, x=0, y=1.12, xref="paper", yref="paper", showarrow=False, font=dict(size=14), xanchor="left"),
            # 인덱스 3: 소외 산업 / 약세 그룹 (버튼 클릭 시 교체됨)
            dict(text=summary_ind_lag, x=0, y=1.07, xref="paper", yref="paper", showarrow=False, font=dict(size=14), xanchor="left"),
            
            # 인덱스 4: WEEKLY TOP 5 (고정)
            dict(text=f"🚀 <b>WEEKLY TOP 5:</b> {top5_str}", x=0, y=1.02, xref="paper", yref="paper", showarrow=False, font=dict(size=12, color="#d62728"), xanchor="left"),
            # 인덱스 5: WEEKLY BOTTOM 5 (고정)
            dict(text=f"🔻 <b>WEEKLY BOTTOM 5:</b> {bottom5_str}", x=0, y=0.98, xref="paper", yref="paper", showarrow=False, font=dict(size=12, color="#1f77b4"), xanchor="left")
        ],

        updatemenus=[dict(
            type="buttons", direction="left", x=0, y=1.16, xanchor="left", yanchor="top",
            active=0, showactive=True,
            buttons=[
                dict(label="🏢 산업별 주간", method="update", 
                     args=[{"visible": [True, False]}, 
                           {"annotations[2].text": summary_ind_lead,
                            "annotations[3].text": summary_ind_lag}]),
                dict(label="🤝 그룹사별 주간", method="update", 
                     args=[{"visible": [False, True]}, 
                           {"annotations[2].text": summary_grp_lead,
                            "annotations[3].text": summary_grp_lag}])
            ]
        )],
        
        coloraxis_colorbar=dict(
            title="주간 등락률(%)",
            thickness=20,
            lenmode="fraction", 
            len=0.86, # 본체 높이 조정에 맞춰 최적화
            yanchor="top",
            y=0.94, 
            x=1.01,
            tickvals=[-10, -5, 0, 5, 10],
            ticktext=["-10%", "-5%", "0%", "+5%", "+10%"]
        )
    )

    # [6] 위치 강제 고정 및 호버 동기화
    dashboard.update_traces(domain=dict(y=[0, 0.94]), row=2, col=1)
    dashboard.update_traces(hovertemplate="%{customdata[0]}<extra></extra>", row=2, col=1)

    # [7. 파일 저장]
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
