import os
import re
import pandas as pd
from pathlib import Path
from datetime import datetime
import shutil

# --- [1] 경로 설정 ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_WEEKLY_DIR = BASE_DIR / "data" / "weekly"
DATA_WEEKLY_DIR.mkdir(parents=True, exist_ok=True)

def get_friday_files():
    """하이픈 포함 파일명 패턴 대응 및 금요일 파일 추출"""
    all_files = list(DATA_RAW_DIR.glob("kpi200_*.csv"))
    # 'latest'가 포함된 파일은 제외
    all_files = [f for f in all_files if "latest" not in f.name]
    
    friday_files = []
    for f in all_files:
        try:
            # 하이픈 포함(2026-03-27) 또는 미포함(20260327) 모두 추출
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})|(\d{8})", f.name)
            if not date_match: continue
            
            date_str = date_match.group(0).replace("-", "")
            dt = datetime.strptime(date_str, "%Y%m%d")
            
            # 요일 확인 (4 = 금요일) 및 'close'가 포함된 파일 우선 순위
            if dt.weekday() == 4:
                friday_files.append((dt, f))
        except Exception:
            continue
            
    # 날짜 내림차순 정렬
    friday_files.sort(key=lambda x: x[0], reverse=True)
    return friday_files

def make_weekly_csv():
    """주간 등락률 계산 및 CSV 저장"""
    friday_list = get_friday_files()
    
    if len(friday_list) < 2:
        print("❌ 주간 비교를 위한 금요일 데이터가 부족합니다.")
        return

    # 최신 금요일과 직전 금요일 선정
    this_fri_dt, this_fri_path = friday_list[0]
    last_fri_dt, last_fri_path = friday_list[1]
    
    print(f"📊 Weekly Process: {last_fri_dt.date()} -> {this_fri_dt.date()}")

    # 데이터 로드
    df_this = pd.read_csv(this_fri_path, encoding="utf-8-sig")
    df_last = pd.read_csv(last_fri_path, encoding="utf-8-sig")[['종목명', '현재가']]
    
    # 병합 및 주간 수익률 계산
    df_weekly = pd.merge(df_this, df_last, on='종목명', how='inner', suffixes=('', '_last'))
    df_weekly['등락률'] = ((df_weekly['현재가'] - df_weekly['현재가_last']) / df_weekly['현재가_last'] * 100).round(2)
    
    # 기준시각 라벨 업데이트 (트리맵 제목용)
    weekly_label = f"{last_fri_dt.strftime('%m.%d')}~{this_fri_dt.strftime('%m.%d')} Weekly"
    df_weekly['기준시각'] = weekly_label

    # 파일 저장
    output_name = f"weekly_kpi200_{this_fri_dt.strftime('%Y%m%d')}.csv"
    output_path = DATA_WEEKLY_DIR / output_name
    df_weekly.to_csv(output_path, index=False, encoding="utf-8-sig")
    
    print(f"✅ 주간 CSV 생성 완료: {output_path.name}")

if __name__ == "__main__":
    make_weekly_csv()
