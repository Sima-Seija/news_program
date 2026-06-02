from flask import Flask, render_template, jsonify
import json
import pymysql
import jieba
from collections import Counter
import re
import os
from dotenv import load_dotenv

# 加載 .env 文件
load_dotenv()

app = Flask(__name__)

db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME', 'propaganda_radar'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# 驗證必需的環境變數
if not db_config['password']:
    raise ValueError("DB_PASSWORD 環境變數未設置。請設置此變數或使用 .env 文件。")

def get_db_connection():
    return pymysql.connect(**db_config)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/media_stats')
def media_stats():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT media_source, AVG(spin_degree) as avg_spin FROM articles GROUP BY media_source")
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/technique_stats')
def technique_stats():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT analysis FROM articles WHERE analysis IS NOT NULL")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        counts = Counter()
        for row in rows:
            analysis = row.get('analysis')
            if not analysis:
                continue
            if isinstance(analysis, str):
                try:
                    analysis = json.loads(analysis)
                except Exception:
                    continue
            technique_ids = analysis.get('technique_ids') if isinstance(analysis, dict) else []
            if isinstance(technique_ids, str):
                try:
                    technique_ids = json.loads(technique_ids)
                except Exception:
                    technique_ids = []
            if not technique_ids:
                continue
            for tid in technique_ids:
                try:
                    counts[int(tid)] += 1
                except Exception:
                    continue

        result = [
            {'technique_id': tid, 'count': count}
            for tid, count in counts.most_common(10)
        ]
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- 修正後的時間趨勢 API ---
@app.route('/api/time_series')
def time_series():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # 直接抓取日期，不使用 MySQL 的 DATE_FORMAT 避免百分比符號衝突
        query = """
            SELECT DATE(publish_time) as date_val, AVG(spin_degree) as avg_spin
            FROM articles
            GROUP BY date_val
            ORDER BY date_val ASC
        """
        cursor.execute(query)
        result = cursor.fetchall()
        cursor.close()
        conn.close()

        # 在 Python 中將 date 物件轉換為 yyyy-mm-dd 字串
        formatted_data = []
        for row in result:
            formatted_data.append({
                "date": row['date_val'].strftime('%Y-%m-%d') if row['date_val'] else "未知",
                "avg_spin": float(row['avg_spin'])
            })
        return jsonify(formatted_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- 修正後的關鍵字雲 API ---
@app.route('/api/keywords')
def keywords():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT analysis FROM articles WHERE analysis IS NOT NULL")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        quotes = []
        for row in rows:
            analysis = row.get('analysis')
            if not analysis:
                continue
            if isinstance(analysis, str):
                try:
                    analysis = json.loads(analysis)
                except Exception:
                    continue
            details = analysis.get('analysis_details') if isinstance(analysis, dict) else []
            if isinstance(details, dict):
                details = [details]
            for item in details:
                quote_text = item.get('quote')
                if quote_text:
                    quotes.append(str(quote_text))

        if not quotes:
            return jsonify([])

        # 合併文字
        all_text = " ".join(quotes)
        
        # 使用 jieba 斷詞
        words = jieba.lcut(all_text)
        
        # 停用詞與規則過濾
        filtered_words = [
            word for word in words 
            if len(word) > 1 and re.match(r'^[\u4e00-\u9fa5]+$', word)
        ]
        
        word_counts = Counter(filtered_words).most_common(100)
        output = [{"name": k, "value": v} for k, v in word_counts]
        return jsonify(output)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 啟動代碼務必放在最下方
if __name__ == '__main__':
    app.run(debug=True, port=5000, host='127.0.0.1')