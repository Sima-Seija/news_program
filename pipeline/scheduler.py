import json
import os
import sys
import time
import re
import webbrowser
import subprocess
import pymysql
from apscheduler.schedulers.blocking import BlockingScheduler
import google.generativeai as genai
from datetime import datetime

# 配置 Gemini API
API_KEY = os.getenv('GOOGLE_API_KEY')
if not API_KEY:
    raise ValueError("GOOGLE_API_KEY 環境變數未設置。請設置此變數或使用 .env 文件。")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('models/gemini-flash-latest')

# Dashboard URL
DASHBOARD_URL = 'http://127.0.0.1:5000/'
ROOT_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
RAW_ARTICLES_DIR = os.path.normpath(os.path.join(ROOT_DIR, 'news_crawler-main', 'raw_articles'))
ANALYSIS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), 'analysis_results'))
CRAWLER_STATE_PATH = os.path.normpath(os.path.join(ROOT_DIR, 'news_crawler-main', '.crawl_state.json'))

# MySQL 配置 - 從環境變數讀取
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME', 'propaganda_radar'),
    'charset': 'utf8mb4'
}

# 驗證必需的環境變數
if not DB_CONFIG['password']:
    raise ValueError("DB_PASSWORD 環境變數未設置。請設置此變數或使用 .env 文件。")

ERROR_LOG_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), 'error_logs'))

# ===== API 限制優化配置 (適用於 Google API 免費方案) =====
MAX_GEMINI_RETRIES = 5
GEMINI_RETRY_DELAY_BASE = 60  # 基礎延遲改為 60 秒（指數退避）
MAX_BATCH_SIZE = 3  # 每次批量分析最多 3 篇文章
INTER_BATCH_DELAY = 90  # 批次間隔 90 秒（避免速率限制）
PIPELINE_INTERVAL_HOURS = 4  # Pipeline 運行間隔：從 1 小時改為 4 小時
MAX_ARTICLES_PER_RUN = 3  # 每次爬蟲最多 3 篇文章（從 5 改為 3）


def get_db_connection():
    return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **DB_CONFIG)


def extract_json_payload(text):
    if not isinstance(text, str):
        return text
    cleaned = text.strip()
    # 移除 markdown code fence
    if cleaned.startswith('```') and cleaned.endswith('```'):
        cleaned = cleaned.strip('`').strip()
    # 移除前置的 json 標記
    cleaned = re.sub(r'^(json\s*)', '', cleaned, flags=re.IGNORECASE).strip()
    # 若符合整段 JSON 格式，直接回傳
    if cleaned.startswith('{') and cleaned.endswith('}'):
        return cleaned
    # 否則尋找第一個 { 和最後一個 }
    start = cleaned.find('{')
    end = cleaned.rfind('}')
    if start != -1 and end != -1 and end > start:
        return cleaned[start:end+1]
    return cleaned


def verify_database_connection():
    try:
        conn = get_db_connection()
        conn.close()
        print('MySQL 連線正常。')
        return True
    except Exception as e:
        print(f'MySQL 連線失敗：{e}')
        return False

# 載入 persuasion techniques
with open(os.path.join(ROOT_DIR, 'persuasion techniques.json'), 'r', encoding='utf-8') as f:
    TECHNIQUES = json.load(f)

# 載入 prompts
with open(os.path.join(ROOT_DIR, 'prompts.md'), 'r', encoding='utf-8') as f:
    PROMPTS = f.read()

def create_database_and_table():
    """創建資料庫和表"""
    connection = pymysql.connect(host=DB_CONFIG['host'], user=DB_CONFIG['user'], password=DB_CONFIG['password'])
    try:
        with connection.cursor() as cursor:
            cursor.execute("CREATE DATABASE IF NOT EXISTS propaganda_radar CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            cursor.execute("USE propaganda_radar;")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    article_id INT AUTO_INCREMENT PRIMARY KEY,
                    media_source VARCHAR(100) NOT NULL COMMENT 'news source',
                    title VARCHAR(500) NOT NULL COMMENT 'news title',
                    publish_time DATETIME COMMENT 'publish time',
                    is_propaganda TINYINT(1) DEFAULT 0 COMMENT 'is propaganda',
                    spin_degree INT DEFAULT 0 COMMENT 'spin degree',
                    technique_ids JSON,
                    analysis JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS raw_articles (
                    raw_id INT AUTO_INCREMENT PRIMARY KEY,
                    source VARCHAR(100),
                    title TEXT,
                    published_at DATETIME,
                    content LONGTEXT,
                    url TEXT,
                    analysis JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
        connection.commit()
    finally:
        connection.close()

def get_processed_news():
    """獲取已處理的新聞標題"""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT title FROM articles;")
            return {row['title'] for row in cursor.fetchall()}
    finally:
        connection.close()

def parse_int_value(value):
    if value is None:
        return 0
    if isinstance(value, str):
        cleaned = value.strip().replace('%', '').replace(',', '').strip()
        try:
            return int(float(cleaned))
        except Exception:
            return 0
    try:
        return int(value)
    except Exception:
        return 0


def insert_raw_article(news):
    """插入原始新聞到 raw_articles"""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
                INSERT INTO raw_articles (source, title, published_at, content, url)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                news.get('source'),
                news.get('title'),
                news.get('published_at'),
                news.get('content'),
                news.get('url')
            ))
            raw_id = cursor.lastrowid
        connection.commit()
        return raw_id
    finally:
        connection.close()

def update_raw_article_analysis(raw_id, analysis):
    """將分析結果寫回 raw_articles"""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
                UPDATE raw_articles
                SET analysis = %s
                WHERE raw_id = %s
            """
            cursor.execute(sql, (
                json.dumps(analysis, ensure_ascii=False),
                raw_id
            ))
        connection.commit()
    finally:
        connection.close()

def insert_analysis_result(news, result):
    """插入分析結果到 articles"""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            technique_ids = result.get('technique_ids') or result.get('宣傳手法編號') or []
            if technique_ids is None:
                technique_ids = []
            sql = """
                INSERT INTO articles (
                    media_source, title, publish_time, is_propaganda, spin_degree,
                    technique_ids, analysis
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                news.get('source'),
                result.get('title') or result.get('新聞標題') or news.get('title'),
                result.get('publish_time') or result.get('發布時間') or news.get('published_at'),
                parse_int_value(result.get('is_propaganda') or result.get('是否為風向文')),
                parse_int_value(result.get('spin_degree') or result.get('帶風向程度')),
                json.dumps(technique_ids, ensure_ascii=False),
                json.dumps(result, ensure_ascii=False)
            ))
            article_id = cursor.lastrowid
        connection.commit()
        return article_id
    finally:
        connection.close()

def _save_gemini_error_log(title, source, response_text, error):
    os.makedirs(ERROR_LOG_DIR, exist_ok=True)
    filename = f"gemini_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    path = os.path.join(ERROR_LOG_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f"title: {title}\n")
        f.write(f"source: {source}\n")
        f.write(f"time: {datetime.now().isoformat()}\n")
        f.write(f"error: {repr(error)}\n\n")
        f.write("response:\n")
        f.write(response_text or "<empty>")
    print(f"已記錄 Gemini 錯誤檔案：{path}")


def analyze_news_with_gemini(content, title, source):
    """使用 Gemini API 分析新聞"""
    prompt = f"""
{PROMPTS}

新聞資料：
{{
  "source": "{source}",
  "title": "{title}",
  "content": "{content}"
}}

請根據以上規則分析這則新聞，並以 JSON 格式輸出結果。
"""

    for attempt in range(1, MAX_GEMINI_RETRIES + 1):
        try:
            response = model.generate_content(prompt)
            result_text = getattr(response, 'text', str(response)).strip()
            if not result_text:
                raise ValueError('empty Gemini response')
            result_text = extract_json_payload(result_text)
            try:
                return json.loads(result_text)
            except json.JSONDecodeError as decode_err:
                print(f"Gemini 回應非 JSON（第 {attempt} 次）：{decode_err}")
                print(f"回應內容前 500 字：{result_text[:500]}")
                _save_gemini_error_log(title, source, result_text, decode_err)
                if attempt < MAX_GEMINI_RETRIES and any(term in result_text.lower() for term in ['quota', 'rate limit', '429']):
                    delay = GEMINI_RETRY_DELAY_BASE * (2 ** (attempt - 1))  # 指數退避
                    print(f"遇到配額或速率限制，等待 {delay} 秒後重試")
                    time.sleep(delay)
                    continue
                return None
        except Exception as e:
            msg = str(e)
            print(f"Gemini API 錯誤（第 {attempt} 次）：{msg}")
            response_text = None
            if 'response' in locals() and response is not None:
                response_text = getattr(response, 'text', None)
            _save_gemini_error_log(title, source, response_text, e)
            if attempt < MAX_GEMINI_RETRIES and any(term in msg.lower() for term in ['quota', 'rate limit', '429']):
                delay = GEMINI_RETRY_DELAY_BASE * (2 ** (attempt - 1))  # 指數退避
                print(f"遇到配額或速率限制，等待 {delay} 秒後重試")
                time.sleep(delay)
                continue
            return None
    return None


def analyze_news_batch_with_gemini(batch_news_list):
    """
    批量分析新聞 - 一次 API 調用分析多篇文章
    batch_news_list: list of dict, each with 'title', 'content', 'source'
    Returns: dict mapping title -> analysis result
    """
    if not batch_news_list:
        return {}
    
    # 如果只有一篇，使用單篇分析函數更穩定
    if len(batch_news_list) == 1:
        news = batch_news_list[0]
        analysis = analyze_news_with_gemini(news.get('content'), news.get('title'), news.get('source'))
        if analysis:
            return {news.get('title'): analysis}
        return {}
    
    # 構建批量分析提示
    batch_content = json.dumps([
        {
            "source": news.get('source'),
            "title": news.get('title'),
            "content": news.get('content')[:1000] if news.get('content') else ""  # 限制每篇內容字數
        }
        for news in batch_news_list
    ], ensure_ascii=False)
    
    prompt = f"""
{PROMPTS}

請對以下 {len(batch_news_list)} 則新聞進行分析，每則新聞的結果以 JSON 物件表示，以 JSON 陣列形式回傳所有結果。

新聞資料：
{batch_content}

重要：請確保回傳的是 JSON 陣列格式，每個元素對應一則新聞，順序不變。
"""

    for attempt in range(1, MAX_GEMINI_RETRIES + 1):
        try:
            print(f"批量分析 {len(batch_news_list)} 篇文章（第 {attempt} 次）...")
            response = model.generate_content(prompt)
            result_text = getattr(response, 'text', str(response)).strip()
            if not result_text:
                raise ValueError('empty Gemini response')
            
            result_text = extract_json_payload(result_text)
            results = json.loads(result_text)
            
            # 確保結果是陣列
            if not isinstance(results, list):
                if isinstance(results, dict):
                    results = [results]
                else:
                    print(f"警告：批量分析結果格式不是列表：{type(results)}")
                    return {}
            
            # 將結果映射到標題，確保順序對應
            result_map = {}
            for i, result in enumerate(results):
                if i < len(batch_news_list):
                    title = batch_news_list[i].get('title')
                    if title and isinstance(result, dict):
                        result_map[title] = result
                        print(f"  ✓ 分析完成：{title[:50]}...")
            
            print(f"批量分析成功：{len(result_map)}/{len(batch_news_list)} 篇文章已分析")
            return result_map
            
        except json.JSONDecodeError as decode_err:
            print(f"批量分析：Gemini 回應非 JSON（第 {attempt} 次）：{decode_err}")
            print(f"回應內容前 500 字：{result_text[:500] if 'result_text' in locals() else 'N/A'}")
            if attempt < MAX_GEMINI_RETRIES and 'result_text' in locals() and any(term in result_text.lower() for term in ['quota', 'rate limit', '429']):
                delay = GEMINI_RETRY_DELAY_BASE * (2 ** (attempt - 1))
                print(f"遇到配額限制，批量分析等待 {delay} 秒後重試")
                time.sleep(delay)
                continue
            # JSON 解析失敗時，嘗試逐篇分析
            if attempt == MAX_GEMINI_RETRIES:
                print(f"批量分析失敗，改為逐篇分析...")
                result_map = {}
                for news in batch_news_list:
                    analysis = analyze_news_with_gemini(news.get('content'), news.get('title'), news.get('source'))
                    if analysis:
                        result_map[news.get('title')] = analysis
                        print(f"  ✓ 逐篇分析完成：{news.get('title')[:50]}...")
                    time.sleep(5)  # 逐篇時增加延遲
                return result_map
        except Exception as e:
            msg = str(e)
            print(f"批量分析 API 錯誤（第 {attempt} 次）：{msg}")
            if attempt < MAX_GEMINI_RETRIES and any(term in msg.lower() for term in ['quota', 'rate limit', '429', 'resource_exhausted']):
                delay = GEMINI_RETRY_DELAY_BASE * (2 ** (attempt - 1))
                print(f"遇到配額限制，批量分析等待 {delay} 秒後重試")
                time.sleep(delay)
                continue
    
    # 所有重試都失敗，返回空字典
    print("批量分析所有重試均失敗")
    return {}


def check_gemini_api():
    """簡單測試 Gemini API 是否可用"""
    health_prompt = "請回覆純文字：OK"
    try:
        response = model.generate_content(health_prompt)
        text = response.text.strip()
        if "OK" in text:
            print("Gemini API 運作正常。")
            return True
        print(f"Gemini API 回應不正確：{text}")
    except Exception as e:
        print(f"Gemini API 檢查失敗：{e}")
    return False


def make_timestamped_path(directory: str, prefix: str, suffix: str) -> str:
    os.makedirs(directory, exist_ok=True)
    return os.path.join(directory, f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{suffix}")


def run_pipeline():
    """執行 pipeline"""
    print("=" * 60)
    print(f"開始執行 pipeline... [{datetime.now().isoformat()}]")
    print("=" * 60)

    os.makedirs(RAW_ARTICLES_DIR, exist_ok=True)
    os.makedirs(ANALYSIS_DIR, exist_ok=True)

    raw_file = make_timestamped_path(RAW_ARTICLES_DIR, 'raw_news', 'json')
    analysis_file = make_timestamped_path(ANALYSIS_DIR, 'analysis', 'json')

    print(f"執行爬蟲，產生原始檔案：{raw_file}")
    print(f"限制：每次最多爬取 {MAX_ARTICLES_PER_RUN} 篇新聞（優化 API 配額）")
    
    try:
        crawler_cmd = [
            sys.executable,
            os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'news_crawler-main', 'politics_news_scraper.py')),
            '--once',
            '--output', raw_file,
            '--latest', os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'news_crawler-main', 'data', 'latest_articles.json')),
            '--state', CRAWLER_STATE_PATH,
            '--max', str(MAX_ARTICLES_PER_RUN),
        ]
        subprocess.run(crawler_cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"爬蟲執行失敗：{e}")
        print("=" * 60)
        print("Pipeline 執行中止（爬蟲失敗）")
        print("=" * 60)
        return

    try:
        with open(raw_file, 'r', encoding='utf-8') as f:
            news_data = json.load(f)
    except Exception as e:
        print(f"讀取爬蟲結果失敗：{e}")
        print("=" * 60)
        print("Pipeline 執行中止（無法讀取爬蟲結果）")
        print("=" * 60)
        return

    if not news_data:
        print("未獲取任何新聞，Pipeline 結束。")
        return

    processed_titles = get_processed_news()
    pending_news = []

    # 過濾已處理的新聞
    for news in news_data:
        if news.get('title') in processed_titles:
            print(f"已跳過已處理新聞：{news.get('title')}")
        else:
            pending_news.append(news)

    if not pending_news:
        print("所有新聞都已處理，Pipeline 結束。")
        return

    print(f"待分析新聞數量：{len(pending_news)} 篇（總爬蟲數：{len(news_data)}）")
    
    analysis_data = []
    successful_count = 0
    failed_count = 0
    
    # 批量分析：分組處理待分析的新聞
    total_batches = (len(pending_news) + MAX_BATCH_SIZE - 1) // MAX_BATCH_SIZE
    for batch_idx, batch_start in enumerate(range(0, len(pending_news), MAX_BATCH_SIZE)):
        batch_end = min(batch_start + MAX_BATCH_SIZE, len(pending_news))
        batch = pending_news[batch_start:batch_end]
        
        print(f"\n--- 批次 {batch_idx + 1}/{total_batches} ---")
        print(f"分析文章 {batch_start + 1} 到 {batch_end}...")
        
        # 先插入原始文章
        batch_with_raw_ids = []
        for news in batch:
            try:
                raw_id = insert_raw_article(news)
                print(f"  寫入原始新聞（raw_id={raw_id}）：{news.get('title')[:50]}...")
                batch_with_raw_ids.append((news, raw_id))
            except Exception as e:
                print(f"  ✗ 插入原始文章失敗：{e}")
                continue
        
        if not batch_with_raw_ids:
            print(f"  警告：批次 {batch_idx + 1} 中沒有成功插入任何原始文章")
            continue
        
        # 批量 API 分析
        batch_results = analyze_news_batch_with_gemini(batch)
        
        # 處理分析結果
        for news, raw_id in batch_with_raw_ids:
            title = news.get('title')
            analysis = batch_results.get(title)
            
            analysis_record = {
                'source': news.get('source'),
                'title': title,
                'published_at': news.get('published_at'),
                'url': news.get('url'),
                'content': news.get('content'),
                'analysis': analysis,
            }
            analysis_data.append(analysis_record)
            
            if analysis:
                try:
                    insert_analysis_result(news, analysis)
                    update_raw_article_analysis(raw_id, analysis)
                    print(f"  ✓ 分析完成：{title[:50]}...")
                    successful_count += 1
                except Exception as e:
                    print(f"  ✗ 保存分析結果失敗：{e}")
                    failed_count += 1
            else:
                print(f"  ✗ 分析失敗（未獲得 API 回應）：{title[:50]}...")
                failed_count += 1
        
        # 批次間延遲
        if batch_end < len(pending_news):
            print(f"批次間隔延遲 {INTER_BATCH_DELAY} 秒（保護 API 配額）...")
            time.sleep(INTER_BATCH_DELAY)

    try:
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"寫入分析結果文件失敗：{e}")

    print("\n" + "=" * 60)
    print(f"Pipeline 執行完成！")
    print(f"成功分析：{successful_count} 篇")
    print(f"失敗分析：{failed_count} 篇")
    print(f"分析結果已寫入：{analysis_file}")
    print("=" * 60)

if __name__ == "__main__":
    if not verify_database_connection():
        print('請先確認 MySQL 服務是否已啟動，並且資料庫連線設定正確。')
        sys.exit(1)

    try:
        create_database_and_table()
    except Exception as ex:
        print(f'建立資料庫或資料表失敗：{ex}')
        sys.exit(1)

    if not check_gemini_api():
        print("Gemini API 檢查失敗，將繼續啟動排程。分析可能會因 API 限制而失敗，請確認金鑰配額與計費狀態。\n")

    print("首次執行 pipeline，請稍候...")
    run_pipeline()

    scheduler = BlockingScheduler()
    
    # 優化：改為每 4 小時運行一次（從 1 小時改為 4 小時，減少 API 調用）
    scheduler.add_job(run_pipeline, 'interval', hours=PIPELINE_INTERVAL_HOURS)

    print("=" * 60)
    print(f"排程啟動，每 {PIPELINE_INTERVAL_HOURS} 小時執行一次 pipeline")
    print(f"單次最多爬取 {MAX_ARTICLES_PER_RUN} 篇文章")
    print(f"批量分析大小：{MAX_BATCH_SIZE}")
    print(f"重試策略：指數退避（基礎延遲 {GEMINI_RETRY_DELAY_BASE} 秒）")
    print("=" * 60)
    
    try:
        webbrowser.open(DASHBOARD_URL, new=2, autoraise=True)
        print(f"已嘗試開啟儀表板：{DASHBOARD_URL}")
    except Exception as e:
        print(f"無法自動開啟瀏覽器：{e}")

    scheduler.start()
