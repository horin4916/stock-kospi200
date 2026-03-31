import os
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import shutil

# --- [1] 경로 및 폴더 설정 ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DOCS_DIR = BASE_DIR / "docs"
DOCS_DAILY_DIR = DOCS_DIR / "daily"

DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DAILY_DIR.mkdir(parents=True, exist_ok=True)

# --- [2] 데이터 로드 로직 ---
def find_latest_csv():
    files = list(DATA_RAW_DIR.glob("kpi200_*.csv"))
    files = [f for f in files if "latest" not in f.name]
    if not files:
        latest_file = DATA_RAW_DIR / "kpi200_latest.csv"
        if latest_file.exists(): return latest_file
        raise FileNotFoundError("데이터 파일(CSV)을 찾을 수 없습니다.")
    return max(files, key=os.path.getmtime)

def load_data(csv_file):
    df = pd.read_csv(csv_file, encoding="utf-8-sig")
    ref_time = str(df["기준시각"].iloc[0]) if not df.empty else "Unknown Time"
    for col in ["그룹사", "1차 분류", "2차 분류", "종목명"]:
        df[col] = df[col].fillna("미분류").astype(str).str.strip()
    for col in ["시가총액", "현재가", "등락률"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["시가총액"] = df["시가총액"].astype(int)
    df["종목_hover"] = df.apply(lambda r: 
        f"<b>{r['종목명']} ({r['그룹사']})</b><br>"
        f"시가총액: {r['시가총액']:,}억<br>"
        f"현재가: {r['현재가']:,}원 ({r['등락률']:+.2f}%)", axis=1)
    return df, ref_time

# --- [3] 메인 실행 함수 ---
def make_dashboard():
    try:
        csv_file = find_latest_csv()
        df, ref_time = load_data(csv_file)
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return

    # [1. 시장 요약 데이터 계산]
    ind_stats = df.groupby('1차 분류')['등락률'].mean()
    strong_1st = ind_stats.idxmax()
    weak_1st = ind_stats.idxmin()
    
    df_g_only = df[df['그룹사'] != '미분류']
    grp_stats = df_g_only.groupby('그룹사')['등락률'].mean() if not df_g_only.empty else None
    strong_grp = grp_stats.idxmax() if grp_stats is not None else "N/A"
    weak_grp = grp_stats.idxmin() if grp_stats is not None else "N/A"
    
    # 등락 종목 1위 (종목명 추출)
    top_stock_name = df.loc[df['등락률'].idxmax(), '종목명']
    top_stock_val = df.loc[df['등락률'].idxmax(), '등락률']
    bottom_stock_name = df.loc[df['등락률'].idxmin(), '종목명']
    bottom_stock_val = df.loc[df['등락률'].idxmin(), '등락률']

    # [2. 대시보드 객체 생성]
    dashboard = make_subplots(
        rows=2, cols=1,
        row_heights=[0.1, 0.9],
        vertical_spacing=0.03,
        specs=[[{"type": "xy"}], [{"type": "treemap"}]]
    )

    # [3. 트리맵 피겨 생성]
    fig_i = px.treemap(df, path=["1차 분류", "2차 분류", "종목명"], values="시가총액", color="등락률", 
                       custom_data=["종목_hover"], color_continuous_scale="RdBu_r", color_continuous_midpoint=0)
    fig_g = px.treemap(df, path=["그룹사", "종목명"], values="시가총액", color="등락률", 
                       custom_data=["종목_hover"], color_continuous_scale="RdBu_r", color_continuous_midpoint=0)

    # [4. 요약 텍스트 구성 (한 줄 통합)]
    summary_ind = (f"📈 <b>강세 산업:</b> {strong_1st} | 📉 <b>약세 산업:</b> {weak_1st} | "
                   f"🚀 <b>상승 1위:</b> {top_stock_name}({top_stock_val:+.2f}%) | 🔻 <b>하락 1위:</b> {bottom_stock_name}({bottom_stock_val:+.2f}%)")

    summary_grp = (f"📈 <b>강세 그룹:</b> {strong_grp} | 📉 <b>약세 그룹:</b> {weak_grp} | "
                   f"🚀 <b>상승 1위:</b> {top_stock_name}({top_stock_val:+.2f}%) | 🔻 <b>하락 1위:</b> {bottom_stock_name}({bottom_stock_val:+.2f}%)")

    # [5. 트리맵 데이터를 대시보드에 추가]
    # fig_i는 인덱스 0번 trace, fig_g는 1번 trace가 됩니다.
    for trace in fig_i.data:
        dashboard.add_trace(trace, row=2, col=1)
    for trace in fig_g.data:
        trace.visible = False
        dashboard.add_trace(trace, row=2, col=1)

    # [6. 레이아웃 업데이트]
    dashboard.update_layout(
        template="plotly_white",
        height=1000, 
        margin=dict(t=210, b=20, l=20, r=80),
        coloraxis_colorscale="RdBu_r",
        coloraxis_cmid=0,
        
        annotations=[
            # 0: 메인제목, 1: 부제
            dict(text="<b>KOSPI 200 Market Map</b>", x=0, y=1.24, xref="paper", yref="paper", showarrow=False, font=dict(size=32), xanchor="left"),
            dict(text=f"기준 시각: {ref_time} | Visualization by HORIN", x=0, y=1.19, xref="paper", yref="paper", showarrow=False, font=dict(size=15, color="gray"), xanchor="left"),
            # 2: 소제목(가변), 3: 요약문(가변)
            dict(text="<b>산업별 트리맵 (Cap-Weighted)</b>", x=0, y=1.075, xref="paper", yref="paper", showarrow=False, font=dict(size=20), xanchor="left"),
            dict(text=summary_ind, x=0, y=1.02, xref="paper", yref="paper", showarrow=False, font=dict(size=13, color="#333"), xanchor="left", align="left")
        ],

        updatemenus=[dict(
            type="buttons", direction="left", x=0, y=1.13, xanchor="left", yanchor="top",
            active=0, showactive=True,
            buttons=[
                dict(label="🏢 산업별 보기", method="update", 
                     args=[{"visible": [False, True, False]}, # XY축(False), 산업별(True), 그룹사별(False)
                           {"annotations[2].text": "<b>산업별 트리맵 (Cap-Weighted)</b>",
                            "annotations[3].text": summary_ind}]),
                dict(label="🤝 그룹사별 보기", method="update", 
                     args=[{"visible": [False, False, True]}, # XY축(False), 산업별(False), 그룹사별(True)
                           {"annotations[2].text": "<b>그룹사별 트리맵 (Cap-Weighted)</b>",
                            "annotations[3].text": summary_grp}])
            ]
        )],
        
        coloraxis_colorbar=dict(
            title="등락률(%)",
            thickness=20,
            lenmode="fraction", 
            # 트리맵 본체 높이(0.96)에 맞춰 컬러바 높이 조정
            len=0.96, 
            # 컬러바의 정렬 기준을 위(top)로 잡고, 트리맵 시작점인 0.96에 배치
            yanchor="top",
            y=0.96, 
            x=1.01,
            # 깔끔하게 보이기 위해 눈금선 간격 설정 (선택 사항)
            tickvals=[-10, -5, 0, 5, 10],
            ticktext=["-10%", "-5%", "0%", "+5%", "+10%"]
        )
    )

    # [7. 트리맵 본체 하향 조정 (겹침 방지 핵심)]
    dashboard.update_traces(domain=dict(y=[0, 0.96]), row=2, col=1)
    
    # 호버 템플릿 강제 적용
    dashboard.update_traces(hovertemplate="%{customdata[0]}<extra></extra>", row=2, col=1)

    # [8. 파일 저장]
    ts = re.sub(r'[^0-9]', '', ref_time)[:12]
    daily_path = DOCS_DAILY_DIR / f"dashboard_{ts}.html"
    dashboard.write_html(str(daily_path), include_plotlyjs="cdn", config={"displaylogo": False})
    shutil.copy(daily_path, DOCS_DIR / "latest.html")
    print(f"✅ 대시보드 저장 완료: {daily_path.name}")

if __name__ == "__main__":
    make_dashboard()
