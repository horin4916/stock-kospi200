import os
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import shutil

# --- [1] GitHub 서버 환경 경로 설정 ---
# 이 스크립트(scripts/...) 위치를 기준으로 프로젝트 루트를 잡습니다.
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DOCS_DIR = BASE_DIR / "docs"
DOCS_DAILY_DIR = DOCS_DIR / "daily"

# 필요한 폴더가 없으면 자동 생성 (Actions 실행 시 안전장치)
DOCS_DAILY_DIR.mkdir(parents=True, exist_ok=True)


# --- [2] 데이터 로드 및 전처리 (최적화) ---

def find_latest_csv():
    """data/raw 폴더에서 가장 최근에 생성된 타임스탬프 CSV를 찾습니다."""
    files = list(DATA_RAW_DIR.glob("kpi200_*.csv"))
    # 'latest.csv'는 제외하고 실제 기록 파일 중 최신을 찾음
    files = [f for f in files if "latest" not in f.name]
    
    if not files:
        # 기록 파일이 없으면 latest.csv라도 시도
        latest_file = DATA_RAW_DIR / "kpi200_latest.csv"
        if latest_file.exists(): return latest_file
        raise FileNotFoundError(f"데이터 파일이 없습니다: {DATA_RAW_DIR}")
        
    # 파일 생성 시간 기준 가장 최신 파일 반환
    return max(files, key=os.path.getmtime)


def load_data(csv_file):
    df = pd.read_csv(csv_file, encoding="utf-8-sig")
    
    # 기준시각 추출 (Unknown 처리)
    ref_time = str(df["기준시각"].iloc[0]) if not df.empty else "Unknown Time"
    
    # 분류값 결측치 처리
    for col in ["그룹사", "1차 분류", "2차 분류", "종목명"]:
        df[col] = df[col].fillna("미분류").astype(str).str.strip()
    
    # 수치형 데이터 변환 및 결측치 0 처리
    for col in ["시가총액", "현재가", "등락률"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    
    df["시가총액"] = df["시가총액"].astype(int)
    df["현재가"] = df["현재가"].astype(int)

    # 대시보드용 호버 텍스트 생성 (f-string 최적화)
    df["종목_hover"] = df.apply(lambda r: 
        f"<b>{r['종목명']} ({r['그룹사']})</b><br>"
        f"시가총액: {r['시가총액']:,}억<br>"
        f"현재가: {r['현재가']:,}원 ({r['등락률']:+.2f}%)", axis=1)
    
    return df, ref_time


# --- [3] 호버 맵 및 요약 로직 (공유해주신 로직 통합) ---

def build_hover_maps(df):
    # 1. 산업별 호버 맵
    lvl1 = df.groupby("1차 분류").agg({"시가총액":"sum", "등락률":"mean"})
    l1_map = {k: f"<b>{k}</b><br>시총: {int(v['시가총액']):,}억<br>평균: {v['등락률']:+.2f}%" for k,v in lvl1.to_dict('index').items()}
    
    lvl2 = df.groupby(["1차 분류", "2차 분류"]).agg({"시가총액":"sum", "등락률":"mean"})
    l2_map = {f"{k[0]}||{k[1]}": f"<b>{k[1]}</b><br>시총: {int(v['시가총액']):,}억<br>평균: {v['등락률']:+.2f}%" for k,v in lvl2.to_dict('index').items()}
    
    # 2. 그룹사별 호버 맵
    grp = df.groupby("그룹사").agg({"시가총액":"sum", "등락률":"mean"})
    g_map = {k: f"<b>{k}</b><br>시총: {int(v['시가총액']):,}억<br>평균: {v['등락률']:+.2f}%" for k,v in grp.to_dict('index').items()}
    
    return l1_map, l2_map, g_map


def apply_custom_hover(fig, hover_map, is_industry=True):
    """트리맵 계층별로 맞춤형 호버 텍스트를 적용합니다."""
    for trace in fig.data:
        if not hasattr(trace, 'ids') or trace.ids is None: continue
            
        hovertexts = []
        for i, node_id in enumerate(trace.ids):
            parts = node_id.split('/')
            
            # Root 또는 1차 분류
            if len(parts) == 1:
                hovertexts.append(hover_map.get(parts[0], ""))
            # 산업별 모드 2차 분류
            elif is_industry and len(parts) == 2:
                key = f"{parts[0]}||{parts[1]}"
                hovertexts.append(hover_map.get(key, ""))
            # 종목
