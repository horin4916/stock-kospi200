import os
import re
import time
import pandas as pd
import requests
from io import StringIO
from pathlib import Path
from bs4 import BeautifulSoup

# --- [GitHub 환경 설정] ---
# 스크립트(scripts/run_kpi200.py) 위치를 기준으로 프로젝트 루트를 잡습니다.
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
SCRIPTS_DIR = BASE_DIR / "scripts"
MASTER_FILE = SCRIPTS_DIR / "kpi200_master.csv"

# 필요한 폴더 강제 생성
DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)

def make_detailed_timestamp(reference_time: str) -> str:
    """
    네이버 기준시각(2026.03.30 15:30)을 읽어 
    '2026-03-30_1530_status' 형식의 상세 파일명을 만듭니다.
    """
    text = str(reference_time).strip()
    
    # 상태값 추출 (장중/장마감/개장전)
    status = "intraday"
    if "장마감" in text: status = "close"
    elif "개장전" in text: status = "preopen"
    
    # 숫자만 추출 (YYYY, MM, DD, HH, MM)
    nums = re.findall(r'\d+', text)
    if len(nums) >= 5:
        return f"{nums[0]}-{nums[1]}-{nums[2]}_{nums[3]}{nums[4]}_{status}"
    
    # 파싱 실패 시 현재 시스템 시간이라도 활용 (안전장치)
    return time.strftime("%Y-%m-%d_%H%M") + f"_{status}"

def fetch_reference_time():
    url = "https://finance.naver.com/sise/sise_index.naver?code=KPI200"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = "euc-kr"
        soup = BeautifulSoup(resp.text, "html.parser")
        time_tag = soup.find(id="time")
        return time_tag.get_text(strip=True) if time_tag else ""
    except:
        return ""

def fetch_kpi200_from_naver() -> pd.DataFrame:
    headers = {"User-Agent": "Mozilla/5.0"}
    all_dfs = []
    seen_first_names = set()

    for page in range(1, 11):
        url = f"https://finance.naver.com/sise/entryJongmok.naver?type=KPI200&page={page}"
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = "euc-kr"

        tables = pd.read_html(StringIO(resp.text))
        df = tables[0].copy()
        df = df.dropna(how="all")
        df = df[df["종목별"].notna()]
        df = df[df["종목별"] != "종목별"]

        if df.empty: break
        if df.iloc[0]["종목별"] in seen_first_names: break
        
        seen_first_names.add(df.iloc[0]["종목별"])
        all_dfs.append(df)
        time.sleep(0.2)

    result = pd.concat(all_dfs, ignore_index=True)
    result = result[["종목별", "시가총액(억)", "현재가", "등락률"]].copy()
    result.columns = ["종목명", "시가총액", "현재가", "등락률"]
    
    # 전처리
    result["종목명"] = result["종목명"].astype(str).str.strip()
    for col in ["시가총액", "현재가"]:
        result[col] = result[col].astype(str).str.replace(",", "").astype(float).astype(int)
    result["등락률"] = result["등락률"].astype(str).str.replace("%", "").str.replace("+", "").astype(float)
    
    return result.sort_values(by="시가총액", ascending=False).reset_index(drop=True)

def run_kpi200():
    # 1. 정보 수집
    ref_time = fetch_reference_time()
    if not ref_time: 
        print("기준 시각 수집 실패로 중단합니다.")
        return

    latest_df = fetch_kpi200_from_naver()
    
    # 2. 마스터 파일 연동 및 업데이트
    if MASTER_FILE.exists():
        master_df = pd.read_csv(MASTER_FILE, encoding="utf-8-sig")
    else:
        master_df = pd.DataFrame(columns=["그룹사", "1차 분류", "2차 분류", "종목명"])

    latest_names = set(latest_df["종목명"])
    master_names = set(master_df["종목명"])
    missing_names = sorted(latest_names - master_names)

    if missing_names:
        new_rows = pd.DataFrame({"그룹사": "", "1차 분류": "", "2차 분류": "", "종목명": missing_names})
        master_df = pd.concat([master_df, new_rows], ignore_index=True)
        master_df.to_csv(MASTER_FILE, index=False, encoding="utf-8-sig")
        print(f"신규 종목 {len(missing_names)}개 마스터 추가 완료")

    # 3. 병합 및 저장
    final_df = pd.merge(latest_df, master_df, on="종목명", how="left")
    final_df.insert(0, "기준시각", ref_time)

    # 타임스탬프 기반 파일명 생성 (예: kpi200_2026-03-30_1530_close.csv)
    ts_filename = make_detailed_timestamp(ref_time)
    
    archive_path = DATA_RAW_DIR / f"kpi200_{ts_filename}.csv"
    latest_path = DATA_RAW_DIR / "kpi200_latest.csv"

    final_df.to_csv(archive_path, index=False, encoding="utf-8-sig")
    final_df.to_csv(latest_path, index=False, encoding="utf-8-sig")

    print(f"✅ 상세 기록 저장: {archive_path.name}")
    print(f"✅ 최신 데이터 갱신: {latest_path.name}")

if __name__ == "__main__":
    run_kpi200()