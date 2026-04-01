import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

# --- [1] 경로 설정 (기존 설정 유지) ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_WEEKLY_DIR = BASE_DIR / "data" / "weekly"
DATA_WEEKLY_DIR.mkdir(parents=True, exist_ok=True)

def get_friday_files():
    """
    파일명에서 날짜를 추출하여 금요일에 해당하는 파일 리스트를 
    날짜 내림차순(최신순)으로 반환합니다.
    """
    all_files = list(DATA_RAW_DIR.glob("kpi200_20*.csv"))
    friday_files = []
    
    for f in all_files:
        # 파일명에서 8자리 날짜 추출 (예: kpi200_20260327_1530.csv -> 20260327)
        date_str = f.name.split('_')[1]
        dt = datetime.strptime(date_str, "%Y%m%d")
        
        # 요일 확인 (4는 금요일)
        if dt.weekday() == 4:
            friday_files.append((dt, f))
            
    # 날짜 기준 내림차순 정렬 (최신 금요일이 0번 인덱스)
    friday_files.sort(key=lambda x: x[0], reverse=True)
    return friday_files

def create_weekly_summary():
    friday_list = get_friday_files()
    
    if len(friday_list) < 2:
        print("❓ 비교할 금요일 파일이 2개 이상 필요합니다. (현재 데이터 부족)")
        return

    this_fri_dt, this_fri_path = friday_list[0]
    last_fri_dt, last_fri_path = friday_list[1]
    
    print(f"📊 주간 비교 시작: {last_fri_dt.date()} ➡️ {this_fri_dt.date()}")

    # 데이터 로드
    df_this = pd.read_csv(this_fri_path, encoding="utf-8-sig")
    df_last = pd.read_csv(last_fri_path, encoding="utf-8-sig")[['종목명', '현재가']]
    
    # 종목명 기준 병합 (전주 데이터는 '현재가_last'로 명명)
    df_weekly = pd.merge(df_this, df_last, on='종목명', how='inner', suffixes=('', '_last'))

    # 주간 등락률 계산: ((이번주 종가 - 전주 종가) / 전주 종가) * 100
    df_weekly['등락률'] = ((df_weekly['현재가'] - df_weekly['현재가_last']) / df_weekly['현재가_last'] * 100).round(2)
    
    # 기준시각 업데이트 (주간 범위 명시)
    weekly_range = f"{last_fri_dt.strftime('%m.%d')}~{this_fri_dt.strftime('%m.%d')}"
    df_weekly['기준시각'] = f"{weekly_range} Weekly"

    # 결과 저장
    output_name = f"weekly_kpi200_{this_fri_dt.strftime('%Y%m%d')}.csv"
    output_path = DATA_WEEKLY_DIR / output_name
    df_weekly.to_csv(output_path, index=False, encoding="utf-8-sig")
    
    print(f"✅ 주간 요약 CSV 저장 완료: {output_path.name}")
    return output_path

if __name__ == "__main__":
    create_weekly_summary()
