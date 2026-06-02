#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
診斷腳本：測試爬蟲和 API 的各個組件
"""
import sys
import os
import json
import time

# 添加路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'news_crawler-main'))

print("=" * 60)
print("新聞爬蟲診斷工具")
print("=" * 60)

# 測試 1: 爬蟲程式導入
print("\n[1/5] 測試爬蟲程式導入...")
try:
    from politics_news_scraper import (
        list_ltn, list_setn, list_tvbs, list_cna,
        parse_ltn_article, parse_setn_article, parse_tvbs_article, parse_cna_article,
        is_politics_content, collect_articles
    )
    print("✓ 爬蟲程式導入成功")
except Exception as e:
    print(f"✗ 爬蟲程式導入失敗：{e}")
    sys.exit(1)

# 測試 2: 各新聞源連接
print("\n[2/5] 測試各新聞源連接...")
sources = [
    ("LTN", list_ltn),
    ("SETN", list_setn),
    ("TVBS", list_tvbs),
    ("CNA", list_cna),
]

for source_name, list_fn in sources:
    try:
        print(f"  正在連接 {source_name}...")
        candidates = list_fn()
        print(f"  ✓ {source_name} 成功：找到 {len(candidates)} 篇候選文章")
        if candidates:
            print(f"    樣本：{candidates[0]['title'][:50]}...")
    except Exception as e:
        print(f"  ✗ {source_name} 失敗：{e}")

# 測試 3: 政治內容檢查
print("\n[3/5] 測試政治內容檢查...")
test_cases = [
    ("民進黨提案", "行政院發言人表示民進黨今天提案修訂稅改條例", True),
    ("天氣預報", "明天氣溫將達 30 度，請做好防曬準備", False),
    ("總統訪日", "我國總統與日本首相會面，商討雙邊關係", True),
]

for title, content, expected in test_cases:
    result = is_politics_content(title, content)
    status = "✓" if result == expected else "✗"
    print(f"  {status} '{title}' -> {result} (期望：{expected})")

# 測試 4: 收集文章
print("\n[4/5] 嘗試收集政治新聞...")
try:
    articles = collect_articles(max_per_source=2)
    print(f"✓ 成功收集 {len(articles)} 篇文章")
    for i, article in enumerate(articles, 1):
        print(f"  {i}. [{article['source']}] {article['title'][:50]}...")
except Exception as e:
    print(f"✗ 收集文章失敗：{e}")

# 測試 5: 資料庫連接
print("\n[5/5] 測試資料庫連接...")
try:
    import pymysql
    db_config = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': '31287532',
        'database': 'propaganda_radar',
        'charset': 'utf8mb4'
    }
    conn = pymysql.connect(**db_config)
    conn.close()
    print("✓ MySQL 資料庫連接成功")
except Exception as e:
    print(f"✗ MySQL 資料庫連接失敗：{e}")
    print("  請檢查 MySQL 是否已啟動，以及連接設定是否正確")

print("\n" + "=" * 60)
print("診斷完成！")
print("=" * 60)
