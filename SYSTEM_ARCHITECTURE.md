# 新聞政治宣傳監測系統 - 系統架構圖

## 完整系統架構

```mermaid
graph LR
    A["使用者"] -->|訪問Web界面| B["爬蟲管理頁面<br/>dashboard.py"]
    A -->|訪問統計| C["媒體儀表板<br/>media_dashboard"]
    
    B -->|控制| D["新聞爬蟲<br/>politics_news_scraper.py"]
    
    D -->|抓取| E["新聞來源"]
    E -->|LTN自由時報| E1["news.ltn.com.tw"]
    E -->|SETN三立新聞| E2["setn.com"]
    E -->|TVBS新聞| E3["news.tvbs.com.tw"]
    E -->|CNA中央社| E4["cna.com.tw"]
    
    D -->|過濾及清洗| F["資料處理模組"]
    F -->|clean_text| F1["文本清洗"]
    F -->|page_text| F2["HTML解析"]
    F -->|is_politics_content| F3["政治內容過濾"]
    
    F -->|輸出| G["JSON檔案<br/>data/latest_articles.json"]
    
    G -->|讀取| H["分析管線<br/>scheduler.py"]
    
    H -->|發送| I["Gemini AI API"]
    
    I -->|使用配置| J["分析規則"]
    J -->|prompts.md| J1["分析提示詞"]
    J -->|persuasion techniques.json| J2["23種宣傳技巧定義"]
    
    I -->|返回| K["分析結果<br/>宣傳技巧識別<br/>帶風向程度"]
    
    K -->|儲存| L["MySQL資料庫<br/>propaganda_radar"]
    
    L -->|查詢| C
    
    C -->|提供API| M["前端應用<br/>templates/index.html"]
    
    M -->|渲染| N["使用者瀏覽器"]
    N -->|顯示| O["統計圖表<br/>分析結果"]

    style A fill:#e1f5ff
    style B fill:#fff9c4
    style C fill:#c8e6c9
    style D fill:#ffe0b2
    style E fill:#ffccbc
    style F fill:#f0f4c3
    style H fill:#d1c4e9
    style I fill:#b3e5fc
    style L fill:#ffccbc
    style N fill:#c8e6c9
```

---

## 資料流動詳細圖

```mermaid
graph TD
    User["最終使用者"]
    
    subgraph "1_爬蟲層"
        Scraper["politics_news_scraper.py<br/>爬蟲主程式"]
        Sources["新聞來源<br/>LTN/SETN/TVBS/CNA"]
    end
    
    subgraph "2_資料處理層"
        Request["HTTP請求<br/>get_html"]
        Parse["HTML解析<br/>BeautifulSoup"]
        Clean["資料清洗<br/>clean_text<br/>page_text"]
        Filter["內容過濾<br/>is_politics_content"]
    end
    
    subgraph "3_儲存層"
        JSON["JSON檔案<br/>raw_articles/<br/>data/latest_articles.json"]
        State["狀態檔案<br/>.crawl_state.json"]
    end
    
    subgraph "4_分析層"
        Scheduler["scheduler.py<br/>分析管線"]
        APICall["Gemini API<br/>調用"]
        Analysis["分析模型<br/>宣傳技巧識別<br/>帶風向程度計算"]
    end
    
    subgraph "5_資料庫層"
        MySQL["MySQL<br/>propaganda_radar"]
        ArticlesTable["articles表<br/>title/source/spin_degree<br/>technique_ids/analysis"]
    end
    
    subgraph "6_展示層"
        DashApp["media_dashboard/app.py"]
        APIs["REST APIs<br/>/api/media_stats<br/>/api/technique_stats<br/>/api/time_series"]
        Frontend["HTML/CSS/JS<br/>前端界面"]
    end
    
    User -->|使用| DashApp
    DashApp -->|查詢| MySQL
    MySQL -->|包含| ArticlesTable
    
    Scheduler -->|讀取| JSON
    Scheduler -->|調用| APICall
    APICall -->|返回結果| Analysis
    Analysis -->|儲存| MySQL
    
    State -->|追蹤| Scraper
    
    Scraper -->|1.請求| Request
    Request -->|2.獲取HTML| Sources
    Sources -->|3.返回HTML| Parse
    Parse -->|4.解析| Clean
    Clean -->|5.清洗| Filter
    Filter -->|6.輸出| JSON
    
    DashApp -->|提供| APIs
    APIs -->|返回數據| Frontend
    Frontend -->|展示| User

    style User fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    style Scraper fill:#ffe0b2,stroke:#e65100,stroke-width:2px
    style Sources fill:#ffccbc,stroke:#bf360c,stroke-width:2px
    style JSON fill:#fff9c4,stroke:#f57f17,stroke-width:2px
    style Scheduler fill:#d1c4e9,stroke:#311b92,stroke-width:2px
    style APICall fill:#b3e5fc,stroke:#01579b,stroke-width:2px
    style MySQL fill:#ffccbc,stroke:#bf360c,stroke-width:2px
    style DashApp fill:#c8e6c9,stroke:#1b5e20,stroke-width:2px
    style Frontend fill:#f0f4c3,stroke:#827717,stroke-width:2px
```

---

## 系統模組關係圖

```mermaid
graph LR
    Crawler["爬蟲模組<br/>news_crawler-main"]
    Pipeline["分析管線<br/>pipeline"]
    Dashboard["儀表板<br/>media_dashboard"]
    
    Crawler -->|輸出JSON| Shared["共享資料<br/>data/latest_articles.json"]
    Shared -->|讀取| Pipeline
    
    Pipeline -->|儲存結果| DB["MySQL<br/>propaganda_radar"]
    DB -->|查詢| Dashboard
    
    Dashboard -->|顯示統計| Web["Web界面<br/>前端渲染"]
    
    Config["配置檔<br/>prompts.md<br/>persuasion techniques.json"]
    Config -->|指導分析| Pipeline
    
    Diag["diagnose.py<br/>診斷工具"]
    Diag -->|檢測| Crawler
    Diag -->|檢測| Pipeline
    Diag -->|檢測| Dashboard
    
    style Crawler fill:#ffe0b2
    style Pipeline fill:#d1c4e9
    style Dashboard fill:#c8e6c9
    style DB fill:#ffccbc
    style Config fill:#fff9c4
    style Web fill:#f0f4c3
```

---

## 爬蟲工作流程詳細圖

```mermaid
graph TD
    Start["開始爬蟲"]
    
    Start -->|讀取狀態檔| LoadState["load_state<br/>.crawl_state.json"]
    LoadState -->|獲取已見URL| SeenURLs["seen_urls集合"]
    
    SeenURLs -->|檢查來源| Sources["4個新聞來源"]
    
    Sources -->|LTN| LTN["list_ltn<br/>→ parse_ltn_article"]
    Sources -->|SETN| SETN["list_setn<br/>→ parse_setn_article"]
    Sources -->|TVBS| TVBS["list_tvbs<br/>→ parse_tvbs_article"]
    Sources -->|CNA| CNA["list_cna<br/>→ parse_cna_article"]
    
    LTN -->|提取標題| GetTitle["獲取標題<br/>發布時間<br/>內容"]
    SETN --> GetTitle
    TVBS --> GetTitle
    CNA --> GetTitle
    
    GetTitle -->|清洗文本| CleanText["clean_text函數<br/>移除特殊字符<br/>規範化空格"]
    
    CleanText -->|HTML解析| PageText["page_text函數<br/>移除廣告/導航<br/>提取主要內容"]
    
    PageText -->|內容過濾| PoliticsCheck["is_politics_content<br/>檢查關鍵字<br/>判斷政治相關度"]
    
    PoliticsCheck -->|是政治內容?| Yes{"是"}
    Yes -->|是| AddArticle["新增至結果清單"]
    Yes -->|否| Skip["跳過本文章"]
    
    AddArticle -->|去重檢查| Dedup{"標題已存在?"}
    Dedup -->|是| Skip
    Dedup -->|否| FinalAdd["添加到articles"]
    
    FinalAdd -->|檢查數量| Count{"已達上限?"}
    Count -->|是| SaveResults["保存結果"]
    Count -->|否| LoopNext["繼續下一篇"]
    LoopNext --> Sources
    
    SaveResults -->|儲存JSON| OutputJSON["raw_articles/<br/>politics_news_YYYYMMDD_HHMMSS.json<br/>data/latest_articles.json"]
    
    OutputJSON -->|更新狀態| SaveState["save_state<br/>.crawl_state.json"]
    
    SaveState -->|輸出結果| End["爬蟲完成"]

    style Start fill:#c8e6c9
    style End fill:#c8e6c9
    style PoliticsCheck fill:#fff9c4
    style CleanText fill:#f0f4c3
    style PageText fill:#ffe0b2
    style OutputJSON fill:#ffccbc
```

---

## 分析管線工作流程圖

```mermaid
graph TD
    Start["分析管線啟動"]
    
    Schedule["APScheduler<br/>定時執行<br/>預設每1小時"]
    
    Start --> Schedule
    Schedule -->|觸發| ReadJSON["讀取JSON<br/>data/latest_articles.json"]
    
    ReadJSON --> ParseJSON["解析JSON<br/>獲取文章清單"]
    
    ParseJSON -->|遍歷每篇| ProcessArticle["處理單篇文章"]
    
    ProcessArticle -->|準備提示詞| PreparePrompt["準備Gemini提示<br/>prompts.md<br/>persuasion techniques.json"]
    
    PreparePrompt -->|組合文章內容| CombineData["組合文章標題+內容<br/>+分析規則"]
    
    CombineData -->|發送API請求| APIRequest["調用Gemini API<br/>google-generativeai"]
    
    APIRequest -->|返回| Response["分析結果JSON<br/>is_propaganda: 0/1<br/>spin_degree: 0-100<br/>technique_ids: []<br/>analysis: {}"]
    
    Response -->|驗證結果| Validate["驗證API結果<br/>檢查必要欄位<br/>處理異常"]
    
    Validate -->|成功| Insert["準備插入資料"]
    Validate -->|失敗| ErrorLog["記錄錯誤<br/>error_logs/"]
    
    Insert -->|插入資料庫| DBInsert["INSERT INTO articles<br/>MySQL<br/>propaganda_radar"]
    
    DBInsert -->|檢查| NextArticle{"還有文章?"}
    NextArticle -->|是| ProcessArticle
    NextArticle -->|否| Complete["分析完成"]
    
    ErrorLog -->|繼續| NextArticle
    
    Complete -->|下次執行| Schedule

    style Start fill:#c8e6c9
    style APIRequest fill:#b3e5fc
    style DBInsert fill:#ffccbc
    style Response fill:#fff9c4
    style ErrorLog fill:#ffccbc
```

---

## 資料庫層次結構

```mermaid
graph TD
    subgraph "MySQL Server"
        DB["propaganda_radar<br/>資料庫"]
        
        DB -->|包含| Table1["articles表"]
        DB -->|包含| Table2["raw_articles表<br/>可選"]
        
        Table1 -->|欄位| F1["article_id PK"]
        Table1 -->|欄位| F2["media_source"]
        Table1 -->|欄位| F3["title"]
        Table1 -->|欄位| F4["publish_time"]
        Table1 -->|欄位| F5["is_propaganda"]
        Table1 -->|欄位| F6["spin_degree 0-100"]
        Table1 -->|欄位| F7["technique_ids JSON"]
        Table1 -->|欄位| F8["analysis JSON"]
        Table1 -->|欄位| F9["created_at"]
    end
    
    style DB fill:#ffccbc,stroke:#bf360c,stroke-width:2px
    style Table1 fill:#fff9c4,stroke:#f57f17,stroke-width:2px
```

---

## 前端API調用圖

```mermaid
graph LR
    Frontend["前端 HTML/JS"]
    
    Frontend -->|GET| API1["/api/media_stats<br/>各媒體統計"]
    Frontend -->|GET| API2["/api/technique_stats<br/>宣傳技巧統計"]
    Frontend -->|GET| API3["/api/time_series<br/>時間序列"]
    
    API1 -->|查詢| Q1["SELECT media_source<br/>AVG spin_degree<br/>GROUP BY source"]
    API2 -->|查詢| Q2["SELECT technique_ids<br/>COUNT frequency"]
    API3 -->|查詢| Q3["SELECT DATE publish_time<br/>AVG spin_degree<br/>GROUP BY date"]
    
    Q1 -->|返回JSON| Result1["媒體平均帶風向度"]
    Q2 -->|返回JSON| Result2["技巧使用頻率"]
    Q3 -->|返回JSON| Result3["日期趨勢數據"]
    
    Result1 -->|渲染| Chart1["柱狀圖"]
    Result2 -->|渲染| Chart2["餅圖/列表"]
    Result3 -->|渲染| Chart3["折線圖"]
    
    Chart1 --> Frontend
    Chart2 --> Frontend
    Chart3 --> Frontend

    style Frontend fill:#c8e6c9
    style API1 fill:#f0f4c3
    style API2 fill:#f0f4c3
    style API3 fill:#f0f4c3
```

---

## 系統配置依賴關係

```mermaid
graph TB
    subgraph "系統入口"
        run_all["run_all.bat<br/>批量啟動腳本"]
    end
    
    subgraph "爬蟲模組"
        crw["news_crawler-main/"]
        crw_reqs["requirements.txt<br/>requests/beautifulsoup4/lxml"]
        scraper["politics_news_scraper.py"]
        dashboard["dashboard.py<br/>Flask"]
    end
    
    subgraph "分析模組"
        pipe["pipeline/"]
        pipe_reqs["requirements.txt<br/>APScheduler<br/>google-generativeai<br/>PyMySQL"]
        scheduler["scheduler.py<br/>Gemini API"]
    end
    
    subgraph "儀表板模組"
        dash["media_dashboard/"]
        dash_reqs["requirements.txt<br/>Flask/PyMySQL/jieba"]
        app["app.py<br/>Flask"]
    end
    
    subgraph "配置文件"
        config1["prompts.md<br/>分析提示詞"]
        config2["persuasion techniques.json<br/>宣傳技巧定義"]
    end
    
    subgraph "環境配置"
        env1["GOOGLE_API_KEY<br/>Gemini API金鑰"]
        env2["MySQL連接設定<br/>host/user/password"]
    end
    
    run_all --> scraper
    run_all --> scheduler
    run_all --> app
    
    crw --> crw_reqs
    crw --> scraper
    crw --> dashboard
    
    pipe --> pipe_reqs
    pipe --> scheduler
    
    dash --> dash_reqs
    dash --> app
    
    scheduler --> config1
    scheduler --> config2
    scheduler --> env1
    scheduler --> env2
    
    app --> env2
    
    scraper --> env2

    style run_all fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    style crw fill:#ffe0b2,stroke:#e65100,stroke-width:2px
    style pipe fill:#d1c4e9,stroke:#311b92,stroke-width:2px
    style dash fill:#c8e6c9,stroke:#1b5e20,stroke-width:2px
    style config1 fill:#fff9c4,stroke:#f57f17,stroke-width:2px
    style config2 fill:#fff9c4,stroke:#f57f17,stroke-width:2px
```

---

## 使用者交互流程

```mermaid
graph TD
    User["使用者"]
    
    subgraph "管理功能"
        User -->|啟動爬蟲| Dashboard["訪問 localhost:8000<br/>爬蟲管理頁面"]
        Dashboard -->|查看結果| ArticleList["新聞清單"]
        Dashboard -->|操作| Ops["編輯/刪除新聞"]
    end
    
    subgraph "分析查閱"
        User -->|查看統計| Analytics["訪問 localhost:5000<br/>媒體儀表板"]
        Analytics -->|查看API| Stats["媒體統計<br/>技巧統計<br/>時間序列"]
        Stats -->|顯示| Charts["圖表展示"]
    end
    
    subgraph "後台自動化"
        Auto["每1小時自動執行"]
        Auto -->|爬取| Crawl["爬蟲執行<br/>新增新聞"]
        Auto -->|分析| Analyze["分析管線執行<br/>更新資料庫"]
        Analyze -->|實時| Charts
    end
    
    Dashboard -.->|觸發| Crawl
    Crawl -->|存儲結果| Charts
    Analyze -->|更新結果| Charts
    
    style User fill:#e1f5ff
    style Dashboard fill:#fff9c4
    style Analytics fill:#c8e6c9
    style Auto fill:#d1c4e9
```

---

## 資訊流完整圖表

```
上層應用層
    ↓
使用者界面層 ← 前端 (HTML/CSS/JS) ← 媒體儀表板 (media_dashboard)
    ↓
API層 ← Flask REST APIs (/api/media_stats, /api/technique_stats, /api/time_series)
    ↓
資料查詢層 ← MySQL Query (SELECT...)
    ↓
資料持久化層 ← MySQL Database (propaganda_radar)
    ↓
分析處理層 ← scheduler.py + Gemini API ← 分析結果 (is_propaganda, spin_degree, technique_ids)
    ↓
JSON資料層 ← data/latest_articles.json ← 爬蟲輸出
    ↓
資料提取層 ← politics_news_scraper.py ← HTTP請求 + HTML解析 + 文本清洗 + 內容過濾
    ↓
資料來源層 ← 外部新聞網站 (LTN/SETN/TVBS/CNA)
    ↓
互聯網層 ← 全球新聞內容
```

---

## 系統組件說明表

| 組件 | 功能 | 技術棧 | 輸入 | 輸出 |
|------|------|--------|------|------|
| **politics_news_scraper.py** | 爬取政治新聞 | requests, BeautifulSoup, lxml | 網站URL | JSON檔案 |
| **dashboard.py** | 爬蟲管理界面 | Flask | 使用者操作 | HTML頁面 |
| **scheduler.py** | 自動分析管線 | APScheduler, Gemini API, PyMySQL | JSON檔案 | MySQL記錄 |
| **app.py (media_dashboard)** | 統計儀表板 | Flask, PyMySQL, jieba | MySQL查詢 | REST API |
| **prompts.md** | AI分析提示 | 文本 | (配置檔) | AI指導 |
| **persuasion techniques.json** | 宣傳技巧定義 | JSON | (配置檔) | 分析規則 |
| **MySQL資料庫** | 資料持久化 | MySQL | INSERT/SELECT | 記錄集合 |

---

**系統架構圖版本**: 1.0  
**最後更新**: 2026年6月2日
