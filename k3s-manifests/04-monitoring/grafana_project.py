import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

# .env 파일 로드 (로컬/서버의 .env 파일을 읽어옵니다)
load_dotenv()

# ================= [설정 정보 - 환경변수 관리] =================
GRAFANA_URL = os.getenv("GRAFANA_URL")
GRAFANA_TOKEN = os.getenv("GRAFANA_TOKEN")
GRAFANA_UID = os.getenv("GRAFANA_UID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")
# ==========================================================

def get_loki_logs():
    print(" 1. Grafana Loki 시스템 로그 수집 중...")
    if not GRAFANA_URL or not GRAFANA_TOKEN:
        print(" 에러: GRAFANA 설정 정보가 .env에 없습니다.")
        return None
        
    url = f"{GRAFANA_URL}/api/ds/query"
    headers = {"Authorization": f"Bearer {GRAFANA_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "queries": [{"refId": "A", "datasource": {"type": "loki", "uid": GRAFANA_UID}, "expr": "{job!=\"\"}", "queryType": "range"}],
        "from": "now-1h", "to": "now"
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        if res.status_code == 200:
            print(" 로그 수집 성공!")
            return str(res.json().get('results', {}).get('A', {}).get('frames', []))[:2000]
    except Exception as e:
        print(f" 에러 발생: {e}")
        return None

def get_gpt_insight(raw_data):
    if not raw_data: return "데이터가 없습니다."
    print(" 2. GPT 시스템 분석 중...")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    prompt = f"아래 시스템 로그 데이터를 분석해서 핵심만 요약해줘 (상태 요약, 특이사항, 권장사항 포함):\n{raw_data}"
    data = {"model": "gpt-4o", "messages": [{"role": "user", "content": prompt}]}
    res = requests.post(url, headers=headers, json=data)
    return res.json()['choices'][0]['message']['content']

def send_to_notion(insight):
    print(" 3. Notion 시스템 리포트 기록 중...")
    url = "https://api.notion.com/v1/pages"
    headers = {"Authorization": f"Bearer {NOTION_TOKEN}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}
    
    payload = {
        "parent": {"database_id": NOTION_DB_ID},
        "properties": {
            "이름": { "title": [{"text": {"content": f"점검_{datetime.now().strftime('%Y-%m-%d %H:%M')}"}}]},
            "내용": { "rich_text": [{"text": {"content": insight[:2000]}}]}
        }
    }
    res = requests.post(url, headers=headers, json=payload)
    if res.status_code == 200:
        print(" 노션 리포트 전송 완료!")
    else:
        print(f" 노션 전송 실패: {res.text}")

if __name__ == "__main__":
    logs = get_loki_logs()
    analysis = get_gpt_insight(logs)
    send_to_notion(analysis)
