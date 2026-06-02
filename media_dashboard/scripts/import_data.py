import json
import pymysql
from datetime import datetime
import os
from dotenv import load_dotenv

# 加載 .env 文件
load_dotenv()

# 1. 資料庫連線設定
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME', 'propaganda_radar'),
    'charset': 'utf8mb4'
}

# 驗證必需的環境變數
if not db_config['password']:
    raise ValueError("DB_PASSWORD 環境變數未設置。請設置此變數或使用 .env 文件。")

def clean_time_string(time_str):
    """處理時間字串，移除（更新時間）內容"""
    if not time_str: return None
    clean_time = time_str.split('（')[0].split('(')[0]
    return clean_time.strip()

def clean_spin_degree(value):
    """處理帶風向程度，將 "40%" 轉換為 40 (整數)"""
    if value is None:
        return 0
    if isinstance(value, str):
        # 移除百分比符號，只留下數字
        value = value.replace('%', '').strip()
        try:
            return int(float(value)) # 先轉 float 再轉 int 可處理像 "20.5" 的情況
        except ValueError:
            return 0
    return int(value)

def import_json_to_mysql(json_file_path):
    try:
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()

        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        success_count = 0
        print("開始匯入資料...")

        for item in data:
            source = item.get("source") or item.get("新聞出處")
            title = item.get("title") or item.get("新聞標題")
            raw_time = item.get("publish_time") or item.get("發布時間")
            
            # 清理時間字串
            clean_time = clean_time_string(raw_time)
            try:
                publish_time = datetime.strptime(clean_time, '%Y/%m/%d %H:%M')
            except Exception:
                # 處理像 2025/11/20 這種沒有分鐘的時間，或解析失敗則跳過
                continue

            is_propaganda = item.get("is_propaganda", item.get("是否為風向文", 0))
            # 處理帶有 % 符號的帶風向程度
            spin_degree = clean_spin_degree(item.get("spin_degree") or item.get("帶風向程度"))
            technique_ids = item.get("technique_ids") or item.get("宣傳手法編號") or []
            analysis_data = item.get("analysis") or item

            # 1. 插入新聞主表
            article_query = """
                INSERT INTO articles (
                    media_source, title, publish_time, is_propaganda, spin_degree,
                    technique_ids, analysis
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(article_query, (
                source,
                title,
                publish_time,
                is_propaganda,
                spin_degree,
                json.dumps(technique_ids, ensure_ascii=False),
                json.dumps(analysis_data, ensure_ascii=False)
            ))
            success_count += 1

        conn.commit()
        print(f"\n✅ 成功匯入 {success_count} 則新聞資料！")

    except pymysql.MySQLError as err:
        print(f"❌ 資料庫錯誤: {err}")
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
    finally:
        if 'conn' in locals() and getattr(conn, 'open', False):
            cursor.close()
            conn.close()

if __name__ == "__main__":
    import_data_path = '../data/gemini.json'
    import_json_to_mysql(import_data_path)