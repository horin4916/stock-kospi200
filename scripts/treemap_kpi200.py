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

    # [1. 기본 시장 요약 데이터 계산]
    total_mcap = df['시가총액'].sum()
    avg_change = df['등락률'].mean()
    up_count = len(df[df['등락률'] > 0])
    down_count = len(df[df['등락률'] < 0])

    # [2. 강화된 요약 정보 계산]
    # 산업별 통계
    ind_stats = df.groupby('1차 분류')['등락률'].mean()
    strong_1st = ind_stats.idxmax()
    weak_1st = ind_stats.idxmin()
    
    # 그룹사별 통계 (미분류 제외)
    df_g_only = df[df['그룹사'] != '미분류']
    grp_stats = df_g_only.groupby('그룹사')['등락률'].mean() if not df_g_only.empty else None
    strong_grp = grp_stats.idxmax() if grp_stats is not None else "N/A"
    weak_grp = grp_stats.idxmin() if grp_stats is not None else "N/A"
    
    # 등락 종목 1위
    top_stock = df.loc[df['등락률'].idxmax()]
    bottom_stock = df.loc[df['등락률'].idxmin()]

    # [3. 버튼별 요약 텍스트 구성]
    summary_ind = (f"📈 <b>강세 산업:</b> {strong_1st} | 📉 <b>약세 산업:</b> {weak_1st}<br>"
                   f"🚀 <b>상승 1위:</b> {top_stock['종목명']}({top_stock['등락률']:+.2f}%) | "
                   f"🔻 <b>하락 1위:</b> {bottom_stock['종목명']}({bottom_stock['등락률']:+.2f}%)")
    
    summary_grp = (f"🏛️ <b>강세 그룹:</b> {strong_grp} | 📉 <b>약세 그룹:</b> {weak_grp}<br>"
                   f"🚀 <b>상승 1위:</b> {top_stock['종목명']}({top_stock['등락률']:+.2f}%) | "
                   f"🔻 <b>하락 1위:</b> {bottom_stock['종목명']}({bottom_stock['등락률']:+.2f}%)")

    # 트리맵 생성
    fig_i = px.treemap(df, path=["1차 분류", "2차 분류", "종목명"], values="시가총액", color="등락률", custom_data=["종목_hover"])
    apply_custom_hover(fig_i, {**l1_m, **l2_m}, is_industry=True)
    
    df_g = df[df['그룹사'] != '미분류']
    fig_g = px.treemap(df_g, path=["그룹사", "종목명"], values="시가총액", color="등락률", custom_data=["종목_hover"])
    apply_custom_hover(fig_g, g_m, is_industry=False)

    # 2. 레이아웃 통합 (공간 최적화)
    dashboard = make_subplots(rows=2, cols=1, row_heights=[0.01, 0.99], vertical_spacing=0,
                              specs=[[{"type": "xy"}], [{"type": "domain"}]])
    
    dashboard.add_trace(go.Scatter(x=[0], y=[0], marker=dict(opacity=0), showlegend=False), row=1, col=1)
    
    for tr in fig_i.data: dashboard.add_trace(tr, row=2, col=1)
    for tr in fig_g.data: 
        tr.visible = False
        dashboard.add_trace(tr, row=2, col=1)

    i_vis = [True] + [True]*len(fig_i.data) + [False]*len(fig_g.data)
    g_vis = [True] + [False]*len(fig_i.data) + [True]*len(fig_g.data)
    
    # 레이아웃 업데이트 (겹침 완전 해결 및 버튼 간격 최적화)
    dashboard.update_layout(
        template="plotly_white",
        height=1000, 
        margin=dict(t=210, b=20, l=20, r=80), 
        
        annotations=[
            # 0번: 메인 제목
            dict(text="<b>KOSPI 200 Market Map</b>", x=0, y=1.24, xref="paper", yref="paper", showarrow=False, font=dict(size=32), xanchor="left"),
            # 1번: 부가 설명
            dict(text=f"기준 시각: {ref_time} | Visualization by HORIN", x=0, y=1.19, xref="paper", yref="paper", showarrow=False, font=dict(size=15, color="gray"), xanchor="left"),
        ],

        updatemenus=[dict(
            type="buttons", direction="left", x=0, y=1.13, xanchor="left", yanchor="top",
            active=0, showactive=True,
            buttons=[
                dict(label="🏢 산업별 보기", method="update", 
                     args=[{"visible": i_vis}, 
                           {"annotations[2].text": "<b>산업별 트리맵 (Cap-Weighted)</b>",
                            "annotations[3].text": summary_ind}]),
                dict(label="🤝 그룹사별 보기", method="update", 
                     args=[{"visible": g_vis}, 
                           {"annotations[2].text": "<b>그룹사별 트리맵 (Cap-Weighted)</b>",
                            "annotations[3].text": summary_grp}])
            ]
        )],
        
        # --- [색상 바] 트리맵이 내려간 만큼 시작 위치(y)와 길이(len) 조정 ---
        coloraxis_colorscale="RdBu_r",
        coloraxis_cmid=0,
        coloraxis_colorbar=dict(
            title="등락률(%)",
            thickness=20,
            lenmode="fraction", 
            len=0.75,          # 트리맵 박스 크기에 맞춰 조정
            yanchor="top",
            y=0.96,            # 트리맵이 시작되는 0.96 지점에 맞춤
            x=1.01
        )
    )

    # [수정] 2번(소제목)과 3번(강화된 요약)의 y값을 조정하여 버튼과 트리맵 사이 중앙에 배치
    extra_annos = (
        # 소제목의 위치를 1.09에서 1.075로 살짝 내려서 버튼과의 간격을 더 확보
        dict(text="<b>산업별 트리맵 (Cap-Weighted)</b>", x=0, y=1.075, xref="paper", yref="paper", showarrow=False, font=dict(size=20), xanchor="left"),
        
        # 요약문의 위치를 1.025에서 1.02로 미세하게 조정하여 소제목-요약문-트리맵 간의 간격을 균등하게 배분
        dict(text=summary_ind, x=0, y=1.02, xref="paper", yref="paper", showarrow=False, font=dict(size=14, color="#333"), xanchor="left", align="left")
    )
    
    dashboard.layout.annotations += extra_annos

    # --- [핵심] 트리맵 본체의 위치를 아래로 강제 이동 ---
    # 트리맵이 차지하는 도메인의 상단 시작점을 0.96으로 낮춰서 위쪽 텍스트 공간 확보
    dashboard.update_traces(domain=dict(y=[0, 0.96]), row=2, col=1)
    
    dashboard.update_xaxes(visible=False, row=1, col=1)
    dashboard.update_yaxes(visible=False, row=1, col=1)

    ts = re.sub(r'[^0-9]', '', ref_time)[:12]
    daily_path = DOCS_DAILY_DIR / f"dashboard_{ts}.html"
    dashboard.write_html(str(daily_path), include_plotlyjs="cdn", config={"displaylogo": False})
    shutil.copy(daily_path, DOCS_DIR / "latest.html")
    print(f"✅ 강화된 대시보드 저장 완료: {daily_path.name}")

if __name__ == "__main__":
    make_dashboard()
