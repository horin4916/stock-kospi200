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

# GitHub Actions 환경에서 폴더가 없으면 에러가 나므로 강제 생성
DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DAILY_DIR.mkdir(parents=True, exist_ok=True)

# --- [2] 데이터 로드 로직 ---
def find_latest_csv():
    """가장 최근에 수집된 CSV 파일을 찾습니다."""
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
    
    # 텍스트 데이터 정제
    for col in ["그룹사", "1차 분류", "2차 분류", "종목명"]:
        df[col] = df[col].fillna("미분류").astype(str).str.strip()
    
    # 수치 데이터 정제
    for col in ["시가총액", "현재가", "등락률"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    
    df["시가총액"] = df["시가총액"].astype(int)
    
    # 호버 텍스트 생성
    df["종목_hover"] = df.apply(lambda r: 
        f"<b>{r['종목명']} ({r['그룹사']})</b><br>"
        f"시가총액: {r['시가총액']:,}억<br>"
        f"현재가: {r['현재가']:,}원 ({r['등락률']:+.2f}%)", axis=1)
    
    return df, ref_time

# --- [3] 호버 메시지 빌더 ---
def build_hover_maps(df):
    # 산업별(1차, 2차) 요약 정보
    l1 = df.groupby("1차 분류").agg({"시가총액":"sum", "등락률":"mean"})
    l1_map = {k: f"<b>{k}</b><br>총 시총: {int(v['시가총액']):,}억<br>평균 등락: {v['등락률']:+.2f}%" for k,v in l1.to_dict('index').items()}
    
    l2 = df.groupby(["1차 분류", "2차 분류"]).agg({"시가총액":"sum", "등락률":"mean"})
    l2_map = {f"{k[0]}||{k[1]}": f"<b>{k[1]}</b><br>총 시총: {int(v['시가총액']):,}억<br>평균 등락: {v['등락률']:+.2f}%" for k,v in l2.to_dict('index').items()}
    
    # 그룹사별 요약 정보
    grp = df.groupby("그룹사").agg({"시가총액":"sum", "등락률":"mean"})
    g_map = {k: f"<b>{k}</b><br>그룹 시총: {int(v['시가총액']):,}억<br>평균 등락: {v['등락률']:+.2f}%" for k,v in grp.to_dict('index').items()}
    
    return l1_map, l2_map, g_map

def apply_custom_hover(fig, hover_map, is_industry=True):
    for trace in fig.data:
        if not hasattr(trace, 'ids') or trace.ids is None: continue
        hovertexts = []
        for i, node_id in enumerate(trace.ids):
            parts = node_id.split('/')
            if len(parts) == 1:
                hovertexts.append(hover_map.get(parts[0], ""))
            elif is_industry and len(parts) == 2:
                hovertexts.append(hover_map.get(f"{parts[0]}||{parts[1]}", ""))
            else:
                hovertexts.append(trace.customdata[i][0] if trace.customdata is not None else "")
        trace.hovertext = hovertexts
        trace.hovertemplate = "%{hovertext}<extra></extra>"

# --- [4] 메인 실행 함수 ---
def make_dashboard():
    try:
        csv_file = find_latest_csv()
        df, ref_time = load_data(csv_file)
    except Exception as e:
        print(f"Error: {e}")
        return

    l1_m, l2_m, g_m = build_hover_maps(df)

    # 시장 요약 데이터 계산 (5번 행용)
    total_mcap = df['시가총액'].sum()
    avg_change = df['등락률'].mean()
    up_count = len(df[df['등락률'] > 0])
    down_count = len(df[df['등락률'] < 0])

    # 1~5번행은 텍스트/버튼 공간, 6번행은 트리맵 공간
    dashboard = make_subplots(
        rows=2, cols=1, 
        row_heights=[0.2, 0.8], # 상단 여백 확보
        vertical_spacing=0.05,
        specs=[[{"type": "xy"}], [{"type": "domain"}]]
    )

    # 산업별 트리맵
    fig_i = px.treemap(df, path=["1차 분류", "2차 분류", "종목명"], values="시가총액", color="등락률", custom_data=["종목_hover"])
    apply_custom_hover(fig_i, {**l1_m, **l2_m}, is_industry=True)
    
    # 그룹사별 트리맵
    df_g = df[df['그룹사'] != '미분류']
    fig_g = px.treemap(df_g, path=["그룹사", "종목명"], values="시가총액", color="등락률", custom_data=["종목_hover"])
    apply_custom_hover(fig_g, g_m, is_industry=False)

    # 배경 축 숨기기용 더미 데이터 (1행)
    dashboard.add_trace(go.Scatter(x=[0], y=[0], marker=dict(opacity=0), showlegend=False), row=1, col=1)
    
    for tr in fig_i.data: dashboard.add_trace(tr, row=2, col=1)
    for tr in fig_g.data: 
        tr.visible = False
        dashboard.add_trace(tr, row=2, col=1)

    # 버튼 가시성 설정
    i_vis = [True] + [True]*len(fig_i.data) + [False]*len(fig_g.data)
    g_vis = [True] + [False]*len(fig_i.data) + [True]*len(fig_g.data)
    
    # 레이아웃 업데이트 (1행부터 순서대로 좌표 지정)
    dashboard.update_layout(
        template="plotly_white",
        height=1000, 
        margin=dict(t=30, b=20, l=20, r=20), # 최상단 여백 최소화
        
        # 주석(Annotations)으로 1, 2, 4, 5행 구현
        annotations=[
            # 1행: 메인 제목 (가장 높게 배치)
            dict(text="<b>KOSPI 200 Market Map</b>", 
                 x=0, y=1.22, xref="paper", yref="paper", showarrow=False, 
                 font=dict(size=28), xanchor="left"),
            
            # 2행: 부가 설명 (제목 바로 아래)
            dict(text=f"기준 시각: {ref_time} | Visualization by HORIN", 
                 x=0, y=1.17, xref="paper", yref="paper", showarrow=False, 
                 font=dict(size=14, color="gray"), xanchor="left"),
            
            # 4행: Treemap 제목 (버튼 아래)
            dict(text="<b>Market Visualization (Cap-Weighted)</b>", 
                 x=0, y=1.04, xref="paper", yref="paper", showarrow=False, 
                 font=dict(size=18), xanchor="left"),
            
            # 5행: 시장 요약 정보
            dict(text=f"시장 요약: 총 시총 {total_mcap:,}억 | 평균 등락 {avg_change:+.2f}% (▲{up_count} ▼{down_count})", 
                 x=0, y=1.00, xref="paper", yref="paper", showarrow=False, 
                 font=dict(size=13, color="#333"), xanchor="left")
        ],

        # 3행: 산업별/그룹사별 버튼 (제목과 트리맵 사이 적절한 높이)
        updatemenus=[dict(
            type="buttons", direction="left", x=0, y=1.12, xanchor="left", yanchor="top",
            active=0, showactive=True,
            buttons=[
                dict(label="🏢 산업별 보기", method="update", args=[{"visible": i_vis}]),
                dict(label="🤝 그룹사별 보기", method="update", args=[{"visible": g_vis}])
            ]
        )],
        
        coloraxis_colorscale="RdBu_r",
        coloraxis_cmid=0,
        coloraxis_colorbar=dict(title="등락률(%)", x=1.02, len=0.7, y=0.4)
    )

    # 눈금선 완전 제거
    dashboard.update_xaxes(visible=False, row=1, col=1)
    dashboard.update_yaxes(visible=False, row=1, col=1)

    # 파일 저장
    ts = re.sub(r'[^0-9]', '', ref_time)[:12]
    daily_path = DOCS_DAILY_DIR / f"dashboard_{ts}.html"
    dashboard.write_html(str(daily_path), include_plotlyjs="cdn", config={"displaylogo": False})
    shutil.copy(daily_path, DOCS_DIR / "latest.html")
    
    print(f"✅ 구조화된 대시보드 저장 완료: {daily_path.name}")

if __name__ == "__main__":
    make_dashboard()
