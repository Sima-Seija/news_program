# Pipeline 腳本

此腳本用於串接爬蟲程式和儀表板，自動化新聞分析流程。

## 功能

- 每小時自動執行爬蟲抓取最新新聞
- 讀取爬蟲產出的 JSON 檔案
- 使用 Gemini API 根據 prompts.md 和 persuasion techniques.json 進行『帶風向程度』與『宣傳手法』分析
- 將分析結果寫入 MySQL 資料庫

## 設定

1. 安裝依賴：
   ```
   python -m pip install -r requirements.txt
   ```
   如果你使用虛擬環境，請先啟動虛擬環境，再執行上面指令。

2. 設定 MySQL：
   - 目前預設連線為 `localhost`，使用者 `root`，密碼 `31287532`
   - 資料庫名稱會建立為 `propaganda_radar`
   - 若你要修改資料庫設定，請編輯 `scheduler.py` 中的 `DB_CONFIG`

3. 確保爬蟲腳本可以執行（`../news_crawler-main/politics_news_scraper.py`）

## 執行

```
python scheduler.py
```

腳本將每小時自動執行一次。

## 資料庫結構

表 `articles`：
- article_id: 主鍵
- media_source: 新聞來源
- title: 標題
- publish_time: 發布時間
- is_propaganda: 是否為風向文 (0/1)
- spin_degree: 帶風向程度 (0-100)
- technique_ids: 宣傳手法編號清單
- analysis: Gemini 分析結果 JSON
- created_at: 建立時間

表 `raw_articles`：
- raw_id: 主鍵
- source: 新聞來源
- title: 標題
- published_at: 發布時間
- content: 原始新聞內容
- url: 新聞網址
- analysis: Gemini 分析結果 JSON
- created_at: 建立時間

## API Rate Limit

Gemini API 有 rate limit，每請求間隔 1 秒以避免超過限制。