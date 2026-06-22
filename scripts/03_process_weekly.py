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

def get_weekly_compare_files():
    """파일명에서 날짜를 파싱하여, 요일과 무관하게 가장 최신 파일과 그 직전 주기 파일을 추출"""
    all_files = list(DATA_RAW_DIR.glob("kpi200_*.csv"))
    # 'latest'가 포함된 파일 및 인트라데이 파일 제외 (확실한 종가 데이터만 타겟팅)
    all_files = [f for f in all_files if "latest" not in f.name and "intraday" not in f.name]
    
    valid_files = []
    for f in all_files:
        try:
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})|(\d{8})", f.name)
            if not date_match: continue
            
            date_str = date_match.group(0).replace("-", "")
            dt = datetime.strptime(date_str, "%Y%m%d")
            
            # 모든 유효한 종가 파일을 리스트에 추가
            valid_files.append((dt, f))
        except Exception:
            continue
            
    # 날짜 내림차순 정렬 (가장 최신 파일이 0번 인덱스로 옴)
    valid_files.sort(key=lambda x: x[0], reverse=True)
    return valid_files

def make_weekly_csv():
    """주간 등락률 계산 및 CSV 저장"""
    file_list = get_weekly_compare_files()
    
    # 비교군이 최소 2개(이번 주 종가, 지난 주 종가)는 있어야 함
    if len(file_list) < 2:
        print("❌ 주간 비교를 위한 데이터 파일이 부족합니다. (최소 2개 이상의 종가 CSV 필요)")
        return

    # 🌟 [로직 변경] 가장 최신 파일과, 영업일 기준 일주일 전(약 5번째 전 파일) 비교
    # 만약 수집된 파일이 적다면 바로 직전 파일[1]과 비교하도록 안정장치 설정
    this_file_dt, this_file_path = file_list[0]
    
    target_index = min(5, len(file_list) - 1) # 5일 전 파일 타겟팅, 부족하면 있는 것 중 가장 오래된 것
    last_file_dt, last_file_path = file_list[target_index]
    
    print(f"📊 Weekly Process 수집 기간: {last_file_dt.date()} ➡️ {this_file_dt.date()}")

    # 데이터 로드
    df_this = pd.read_csv(this_file_path, encoding="utf-8-sig")
    df_last = pd.read_csv(last_file_path, encoding="utf-8-sig")[['종목명', '현재가']]
    
    # 병합 및 주간 수익률 계산
    df_weekly = pd.merge(df_this, df_last, on='종목명', how='inner', suffixes=('', '_last'))
    df_weekly['등락률'] = ((df_weekly['현재가'] - df_weekly['현재가_last']) / df_weekly['현재가_last'] * 100).round(2)
    
    # 기준시각 라벨 업데이트 (트리맵 상단 제목 연동용)
    weekly_label = f"{last_file_dt.strftime('%m.%d')}~{this_file_dt.strftime('%m.%d')} Weekly"
    df_weekly['기준시각'] = weekly_label

    # 파일 저장
    # 🌟 [날짜 보정 추가] 최신 파일의 요일을 확인 (5=토요일, 6=일요일)
    weekday_num = this_fri_dt.weekday()
    label_dt = this_fri_dt

    if weekday_num == 5:     # 만약 토요일이라면 하루를 빼서 금요일로 변경
        label_dt = this_fri_dt - pd.Timedelta(days=1)
    elif weekday_num == 6:   # 만약 일요일이라면 이틀을 빼서 금요일로 변경
        label_dt = this_fri_dt - pd.Timedelta(days=2)

    # 기준시각 라벨 업데이트 (트리맵 제목 연동 시 토요일 대신 금요일 날짜가 뜨도록 보정)
    weekly_label = f"{last_fri_dt.strftime('%m.%d')}~{label_dt.strftime('%m.%d')} Weekly"
    df_weekly['기준시각'] = weekly_label

    # 파일 저장 (이름이 무조건 금요일 날짜 기준으로 생성됨)
    output_name = f"weekly_kpi200_{label_dt.strftime('%Y%m%d')}.csv"
    output_path = DATA_WEEKLY_DIR / output_name
    df_weekly.to_csv(output_path, index=False, encoding="utf-8-sig")
    
    print(f"✅ 주간 CSV 생성 완료: {output_path.name}")

if __name__ == "__main__":
    make_weekly_csv()
