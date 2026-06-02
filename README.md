# news_program
# 新聞政治宣傳監測系統 - 專案說明

## 專案概述

本專案是一個完整的媒體監測系統，用於自動爬取台灣政治新聞，分析文章中的宣傳技巧和帶風向程度，並提供視覺化的統計儀表板。系統架構包括三個主要模組：新聞爬蟲、分析管線和資料可視化。

## 系統功能

1. **新聞爬取** - 自動從多個新聞來源爬取政治新聞
2. **智能過濾** - 使用關鍵字匹配識別政治相關內容
3. **文本分析** - 使用Gemini AI分析宣傳技巧和帶風向程度
4. **資料儲存** - 將分析結果存儲至MySQL資料庫
5. **資料可視化** - 提供兩個Web儀表板展示統計數據和分析結果

---

## 專案結構

```
news_program/
├── news_crawler-main/           # 新聞爬蟲模組
│   ├── politics_news_scraper.py # 爬蟲主程式
│   ├── dashboard.py             # 爬蟲管理頁面
│   ├── requirements.txt          # 爬蟲依賴套件
│   ├── data/                     # 爬蟲輸出資料夾
│   ├── raw_articles/             # 原始爬蟲結果
│   ├── web/                      # 前端界面檔案
│   │   ├── index.html
│   │   ├── app.js
│   │   └── style.css
│   └── README.md
│
├── pipeline/                     # 分析管線模組
│   ├── scheduler.py              # 自動化分析排程
│   ├── requirements.txt          # 管線依賴套件
│   ├── analysis_results/         # 分析結果儲存
│   ├── error_logs/               # 錯誤日誌
│   └── README.md
│
├── media_dashboard/              # 媒體儀表板模組
│   ├── app.py                    # Flask應用主程式
│   ├── static/                   # 靜態資源
│   ├── templates/                # HTML模板
│   │   └── index.html
│   ├── upload/                   # 上傳檔案目錄
│   ├── data/                     # 資料檔案
│   │   └── gpt.json
│   └── scripts/
│       └── import_data.py        # 資料匯入腳本
│
├── prompts.md                    # AI分析提示詞
├── persuasion techniques.json    # 23種宣傳技巧定義
├── diagnose.py                   # 系統診斷工具
├── run_all.bat                   # 批量啟動腳本 (Windows)
└── README_PROJECT.md             # 本檔案

```

---

## 模組詳細說明

### 1. 新聞爬蟲模組 (news_crawler-main)

#### 功能
- 從4個台灣新聞網站爬取政治新聞：LTN自由時報、SETN三立新聞、TVBS新聞、CNA中央通訊社
- 自動進行政治內容過濾
- 支援單次執行和定時自動執行
- 提供Web管理介面查看、編輯、刪除新聞

#### 核心檔案

**politics_news_scraper.py**
- `list_ltn()`, `list_setn()`, `list_tvbs()`, `list_cna()` - 爬取各網站新聞列表
- `parse_ltn_article()`, `parse_setn_article()`, `parse_tvbs_article()`, `parse_cna_article()` - 解析文章內容
- `is_politics_content()` - 政治相關度檢測（支援23個核心政治關鍵字及靈活關鍵字）
- `get_html()` - HTTP請求處理（自動重試機制）
- `clean_text()` - 文本清洗
- `page_text()` - HTML頁面提取

**dashboard.py**
- Flask應用，提供Web管理介面
- 預設運行在 http://127.0.0.1:8000
- 支援新聞CRUD操作

#### 輸出格式
JSON檔案，包含以下欄位：
```json
{
  "source": "LTN",
  "title": "新聞標題",
  "published_at": "2026-06-02 12:00:00",
  "content": "新聞內容",
  "url": "https://..."
}
```

#### 依賴套件
- requests - HTTP請求
- beautifulsoup4 - HTML解析
- lxml - XML/HTML處理

### 2. 分析管線模組 (pipeline)

#### 功能
- 自動讀取爬蟲輸出的JSON檔案
- 使用Google Gemini API進行內容分析
- 根據23種宣傳技巧定義進行識別
- 計算帶風向程度（0-100%）
- 將分析結果儲存至MySQL資料庫

#### 核心檔案

**scheduler.py**
- 使用APScheduler實現定時自動執行（預設每小時執行一次）
- 讀取 `/data/latest_articles.json` 檔案
- 呼叫Gemini API進行分析
- 將結果儲存至MySQL資料庫 `propaganda_radar`

#### 資料庫表結構

**articles表**
| 欄位 | 說明 | 型態 |
|------|------|------|
| article_id | 主鍵 | INT PRIMARY KEY |
| media_source | 新聞來源(LTN/SETN/TVBS/CNA) | VARCHAR |
| title | 新聞標題 | TEXT |
| publish_time | 發布時間 | DATETIME |
| is_propaganda | 是否為風向文(0/1) | TINYINT |
| spin_degree | 帶風向程度百分比 | INT |
| technique_ids | 宣傳技巧ID清單(JSON) | TEXT |
| analysis | 完整分析結果(JSON) | LONGTEXT |
| created_at | 記錄建立時間 | TIMESTAMP |

#### 宣傳技巧分析

系統使用 `persuasion techniques.json` 定義23種宣傳技巧，包括：
- 情感訴求（利用情感而非理性）
- 權威訴求（引用專家或名人）
- 從眾訴求（聲稱大多數人支持）
- 簡化論（過度簡化複雜問題）
- 虛假兩難（只呈現兩個極端選項）
- 人身攻擊（針對人而非論點）
等等

#### 帶風向程度計算規則
- 0% - 無任何宣傳技巧
- 1-30% - 技巧零星，僅局部語句
- 31-70% - 技巧分布於多段，具明顯引導效果
- 71-100% - 高度引導立場的文本，技巧頻繁出現

#### 依賴套件
- APScheduler - 定時排程
- google-generativeai - Gemini API
- PyMySQL - MySQL連線

### 3. 媒體儀表板模組 (media_dashboard)

#### 功能
- 展示多媒體統計數據（各媒體帶風向程度平均值）
- 展示宣傳技巧統計（最常見的10種技巧）
- 提供時間序列圖表（按日期統計帶風向程度趨勢）
- RESTful API接口供前端調用

#### 核心檔案

**app.py**
- Flask應用
- `/` - 主頁面
- `/api/media_stats` - 各媒體統計API
- `/api/technique_stats` - 宣傳技巧統計API
- `/api/time_series` - 時間序列API

**templates/index.html**
- 前端界面

**static/**
- CSS和JavaScript資源

#### 依賴套件
- Flask - Web框架
- PyMySQL - 資料庫連線
- jieba - 中文分詞

---

## 安裝與設定

### 先決條件
- Python 3.8或以上版本
- MySQL 8.0或以上
- Windows系統（或Unix系統，batch指令需調整）

### 第1步：環境設定

1. 克隆或下載專案
   ```powershell
   cd c:\news_program
   ```

2. 建立Python虛擬環境
   ```powershell
   py -3 -m venv .venv-1
   ```

3. 啟用虛擬環境
   ```powershell
   .\.venv-1\Scripts\Activate.ps1
   ```

### 第2步：安裝依賴套件

1. 安裝爬蟲模組依賴
   ```powershell
   cd news_crawler-main
   pip install -r requirements.txt
   cd ..
   ```

2. 安裝管線模組依賴
   ```powershell
   cd pipeline
   pip install -r requirements.txt
   cd ..
   ```

3. 安裝儀表板模組依賴
   ```powershell
   cd media_dashboard
   pip install -r requirements.txt
   cd ..
   ```

### 第3步：MySQL資料庫設定

1. 啟動MySQL服務
   ```powershell
   # Windows上可使用MySQL Command Line Client或其他客戶端
   ```

2. 建立資料庫和使用者（可選，如使用預設設定）
   ```sql
   CREATE DATABASE propaganda_radar CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

3. 確認資料庫連接設定
   - 預設主機：localhost
   - 預設使用者：root
   - 預設密碼：31287532
   - 資料庫名稱：propaganda_radar
   
   若需修改，編輯以下檔案：
   - `pipeline/scheduler.py` 中的 `DB_CONFIG`
   - `media_dashboard/app.py` 中的 `db_config`

### 第4步：Google Gemini API設定

1. 申請Google Gemini API金鑰
   - 訪問 https://makersuite.google.com/app/apikey
   - 建立新的API金鑰

2. 在環境變數中設定API金鑰
   ```powershell
   $env:GOOGLE_API_KEY = "your_api_key_here"
   ```
   
   或在 `pipeline/scheduler.py` 中直接設定（不建議用於生產環境）

---

## 執行指南

### 方式1：個別運行各模組

#### 運行爬蟲（單次執行）
```powershell
# 啟用虛擬環境
.\.venv-1\Scripts\Activate.ps1

# 進入爬蟲目錄
cd news_crawler-main

# 單次爬取（每個來源最多5篇）
py -3 politics_news_scraper.py --once --max 5 --output-dir raw_articles --latest data/latest_articles.json --state .crawl_state.json
```

#### 運行爬蟲（定時自動執行）
```powershell
# 每1小時自動爬取一次
py -3 politics_news_scraper.py --interval-hours 1 --max 5 --output-dir raw_articles --latest data/latest_articles.json --state .crawl_state.json
```

#### 運行爬蟲管理頁面
```powershell
py -3 dashboard.py
```
然後在瀏覽器開啟：http://127.0.0.1:8000

#### 運行分析管線
```powershell
cd ..\pipeline
py -3 scheduler.py
```

#### 運行媒體儀表板
```powershell
cd ..\media_dashboard
py -3 app.py
```
然後在瀏覽器開啟：http://127.0.0.1:5000

### 方式2：使用批量啟動腳本（Windows）

一鍵啟動所有服務：
```powershell
run_all.bat
```

此腳本會依序啟動：
1. 新聞爬蟲管理界面
2. 分析管線排程
3. 媒體儀表板

### 爬蟲命令列參數

```powershell
py -3 politics_news_scraper.py [選項]
```

| 參數 | 簡寫 | 預設值 | 說明 |
|------|------|--------|------|
| --output | -o | (無) | 輸出JSON檔案路徑 |
| --output-dir | | raw_articles | 輸出資料夾 |
| --latest | | data/latest_articles.json | 最新結果檔案路徑 |
| --state | | .crawl_state.json | 爬蟲狀態檔案 |
| --max | | 5 | 每個來源最多爬取篇數 |
| --interval-hours | | 1.0 | 定時爬取間隔（小時） |
| --once | | (無) | 只執行一次並退出 |

---

## 工作流程

### 系統完整流程

1. **爬蟲階段**（每1小時自動執行）
   - 訪問4個新聞網站
   - 抓取最新新聞列表
   - 過濾非政治內容
   - 提取新聞標題、內容、發布時間
   - 去重處理
   - 輸出JSON檔案到 `data/latest_articles.json`

2. **分析階段**（每1小時自動執行）
   - 讀取最新的爬蟲結果
   - 對每篇新聞呼叫Gemini API
   - 根據23種宣傳技巧進行分析
   - 計算帶風向程度
   - 儲存結果至MySQL資料庫

3. **展示階段**
   - 媒體儀表板從資料庫查詢數據
   - 計算各媒體統計
   - 提供API給前端
   - 前端渲染圖表和統計信息

### 資料流向
```
新聞網站 → 爬蟲(politics_news_scraper.py) 
         → JSON檔案(data/latest_articles.json)
         → 分析管線(scheduler.py)
         → Gemini API分析
         → MySQL資料庫(propaganda_radar)
         → 媒體儀表板(media_dashboard/app.py)
         → Web瀏覽器可視化
```

---

## 資料清洗流程

### 文本清洗 (clean_text函數)
- 替換非標準空格（\u00a0）為正常空格
- 移除回車符（\r）和制表符（\t）
- 合併多個連續空格為單個空格
- 移除前後空白

### HTML解析 (page_text函數)
- 移除script、style、noscript標籤
- 移除廣告區域（shareBox、advertiseBox、ads等）
- 移除導航和相關連結
- 過濾推廣文字（「請繼續往下閱讀」、「下載APP」等）
- 只保留有效的文章段落

### 內容過濾 (is_politics_content函數)

**核心政治關鍵字檢測**
- 包含關鍵字：政治、政府、政策、立法院、國會、選舉、民進黨、國民黨等
- 非政治排除詞：天氣、運動、娛樂、財經等
- 靈活判斷：決策、官員、發言、會議等相關詞彙

**過濾規則**
1. 若包含排除關鍵字但無政治關鍵字 → 非政治（過濾）
2. 若包含任何政治核心關鍵字 → 政治內容（保留）
3. 若包含靈活關鍵字且非明顯非政治 → 政治內容（保留）

---

## 故障排除

### 問題1：MySQL連接失敗
**症狀**：Error connecting to MySQL
**解決**：
- 確認MySQL服務已啟動
- 檢查主機名稱、使用者名稱、密碼設定
- 確認資料庫 `propaganda_radar` 已建立
- 檢查防火牆設定

### 問題2：Gemini API錯誤
**症狀**：Authentication failed或invalid_request
**解決**：
- 確認API金鑰正確設定
- 檢查 `GOOGLE_API_KEY` 環境變數
- 確認API配額未超出
- 檢查網路連接

### 問題3：爬蟲無法連接網站
**症狀**：Connection timeout或refused
**解決**：
- 檢查網路連接
- 確認目標網站是否可訪問
- 檢查防火牆/代理設定
- 嘗試手動訪問網站確認可用性

### 問題4：編碼錯誤
**症狀**：UnicodeDecodeError或亂碼
**解決**：
- 已在爬蟲中預設UTF-8編碼
- 檢查MySQL字符集設定（應為utf8mb4）
- 確認編輯器設定為UTF-8

### 問題5：依賴套件安裝失敗
**症狀**：pip install失敗
**解決**：
- 升級pip：`pip install --upgrade pip`
- 清除pip緩存：`pip install --no-cache-dir -r requirements.txt`
- 使用更新的Python版本
- 檢查網路連接

---

## 配置檔說明

### prompts.md
包含發送給Gemini API的系統提示詞，定義分析規則和輸出格式。

### persuasion techniques.json
定義23種宣傳技巧及其描述，作為分析的判斷標準。結構如下：
```json
{
  "techniques": [
    {
      "id": 1,
      "name": "情感訴求",
      "description": "利用情感而非理性進行說服..."
    },
    ...
  ]
}
```

---

## 監控與維護

### 定期檢查項目

1. **爬蟲狀態** - 檢查 `news_crawler-main/.crawl_state.json`
2. **資料庫大小** - 監控 `propaganda_radar` 資料庫增長
3. **API配額** - 確認Gemini API用量
4. **錯誤日誌** - 檢查 `pipeline/error_logs/`
5. **磁碟空間** - 監控 `raw_articles/` 和 `analysis_results/` 大小

### 資料備份

定期備份MySQL資料庫：
```powershell
mysqldump -u root -p propaganda_radar > backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql
```

### 清理過期資料

建議定期清理舊的爬蟲結果檔案：
```powershell
# 刪除30天前的原始爬蟲結果
Get-ChildItem news_crawler-main/raw_articles/*.json | Where-Object {$_.LastWriteTime -lt (Get-Date).AddDays(-30)} | Remove-Item
```

---

## 開發和擴展

### 新增新聞來源

1. 在 `politics_news_scraper.py` 中建立新的 `list_xxx()` 函數
2. 建立對應的 `parse_xxx_article()` 解析函數
3. 在 `collect_articles()` 中新增源
4. 測試爬蟲功能

### 自訂分析模型

修改 `prompts.md` 改變AI分析邏輯

修改 `persuasion techniques.json` 調整宣傳技巧定義

### 擴展資料庫欄位

編輯 `pipeline/scheduler.py` 中的資料庫表定義

---

## 許可證與貢獻

本專案為學術研究和監督新聞宣傳用途。

---

## 聯繫方式與支援

如有技術問題或建議，請檢查以下資源：
- 各模組README檔案
- `diagnose.py` 系統診斷工具
- 錯誤日誌檔案

---

## 更新記錄

### v1.0 (2026-06-02)
- 初始發佈版本0
- 包含爬蟲、分析和儀表板模組
- 支援4個新聞來源
- 集成Gemini API分析
- MySQL資料持久化

---

**最後更新**：2026年6月2日
**系統版本**：1.0
