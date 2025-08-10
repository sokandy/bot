#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票監控數據庫測試腳本
測試 stock_monitor_db.py 的各項功能
"""

import os
import sys
import sqlite3
from datetime import datetime

def test_database_connection():
    """測試數據庫連接"""
    print("🔍 測試數據庫連接...")
    
    try:
        # 測試導入模塊
        from stock_monitor_db import StockMonitorDB
        print("✅ 成功導入 StockMonitorDB 模塊")
        
        # 創建數據庫實例
        monitor_db = StockMonitorDB("test_stock_monitor.db")
        print("✅ 成功創建數據庫實例")
        
        return monitor_db
    except ImportError as e:
        print(f"❌ 導入失敗：{e}")
        return None
    except Exception as e:
        print(f"❌ 創建數據庫實例失敗：{e}")
        return None

def test_add_watch(monitor_db):
    """測試添加監控"""
    print("\n🔍 測試添加股票監控...")
    
    try:
        # 測試添加監控
        success, message = monitor_db.add_watch(12345, 67890, "0005.HK", 50.0)
        print(f"添加監控結果：{success}, {message}")
        
        if success:
            print("✅ 成功添加股票監控")
        else:
            print("❌ 添加股票監控失敗")
            
        return success
    except Exception as e:
        print(f"❌ 添加監控測試失敗：{e}")
        return False

def test_list_watches(monitor_db):
    """測試列出監控"""
    print("\n🔍 測試列出股票監控...")
    
    try:
        watches = monitor_db.list_watches(12345)
        print(f"監控列表：{watches}")
        
        if isinstance(watches, str):
            if "沒有設置任何監控" in watches:
                print("✅ 正確顯示無監控信息")
            else:
                print("✅ 成功獲取監控列表")
        else:
            print("❌ 監控列表格式不正確")
            
        return True
    except Exception as e:
        print(f"❌ 列出監控測試失敗：{e}")
        return False

def test_remove_watch(monitor_db):
    """測試移除監控"""
    print("\n🔍 測試移除股票監控...")
    
    try:
        # 使用不同的用戶ID來避免與前面的測試衝突
        test_user_id = 54321
        test_chat_id = 98765
        
        # 先添加一個監控
        success, message = monitor_db.add_watch(test_user_id, test_chat_id, "0700.HK", 300.0)
        if success:
            print("✅ 成功添加測試監控")
            
            # 獲取監控ID
            watches = monitor_db.list_watches(test_user_id)
            if isinstance(watches, str) and "ID:" in watches:
                # 解析ID
                lines = watches.split('\n')
                watch_id = None
                for line in lines:
                    if 'ID:' in line and '**' in line:
                        # 提取ID，格式是 "🆔 **ID: 1**"
                        id_part = line.split('**')[1]
                        watch_id = int(id_part.split(':')[1].strip())
                        break
                
                if watch_id:
                    print(f"找到監控ID：{watch_id}")
                    # 測試移除
                    success, message = monitor_db.remove_watch(test_user_id, watch_id)
                    print(f"移除監控結果：{success}, {message}")
                    
                    if success:
                        print("✅ 成功移除股票監控")
                        
                        # 驗證是否真的被移除了
                        watches_after = monitor_db.list_watches(test_user_id)
                        if "沒有設置任何股票監控" in watches_after:
                            print("✅ 驗證：監控確實已被移除")
                            return True
                        else:
                            print("❌ 驗證失敗：監控仍然存在")
                            print(f"移除後的監控列表：{watches_after}")
                            return False
                    else:
                        print("❌ 移除股票監控失敗")
                        return False
                else:
                    print("❌ 無法解析監控ID")
                    return False
            else:
                print("⚠️ 無法獲取監控列表進行移除測試")
                return False
        else:
            print("❌ 無法添加測試監控")
            return False
            
    except Exception as e:
        print(f"❌ 移除監控測試失敗：{e}")
        return False

def test_database_structure():
    """測試數據庫結構"""
    print("\n🔍 測試數據庫結構...")
    
    try:
        conn = sqlite3.connect("test_stock_monitor.db")
        cursor = conn.cursor()
        
        # 檢查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"數據庫中的表：{[table[0] for table in tables]}")
        
        # 檢查 stock_watches 表結構
        cursor.execute("PRAGMA table_info(stock_watches)")
        columns = cursor.fetchall()
        print("stock_watches 表結構：")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        
        # 檢查數據
        cursor.execute("SELECT COUNT(*) FROM stock_watches")
        count = cursor.fetchone()[0]
        print(f"stock_watches 表中的記錄數：{count}")
        
        conn.close()
        print("✅ 數據庫結構測試完成")
        return True
    except Exception as e:
        print(f"❌ 數據庫結構測試失敗：{e}")
        return False

def cleanup_test_database():
    """清理測試數據庫"""
    print("\n🧹 清理測試數據庫...")
    
    try:
        if os.path.exists("test_stock_monitor.db"):
            os.remove("test_stock_monitor.db")
            print("✅ 測試數據庫已清理")
        else:
            print("ℹ️ 測試數據庫不存在，無需清理")
    except Exception as e:
        print(f"❌ 清理測試數據庫失敗：{e}")

def main():
    """主測試函數"""
    print("🚀 開始股票監控數據庫測試\n")
    
    # 測試數據庫連接
    monitor_db = test_database_connection()
    if not monitor_db:
        print("\n❌ 數據庫連接測試失敗，停止測試")
        return
    
    # 測試各項功能
    test_results = []
    
    test_results.append(("數據庫結構", test_database_structure()))
    test_results.append(("添加監控", test_add_watch(monitor_db)))
    test_results.append(("列出監控", test_list_watches(monitor_db)))
    test_results.append(("移除監控", test_remove_watch(monitor_db)))
    
    # 顯示測試結果
    print("\n📊 測試結果總結：")
    print("=" * 50)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{test_name:15} : {status}")
        if result:
            passed += 1
    
    print("=" * 50)
    print(f"總計：{passed}/{total} 項測試通過")
    
    if passed == total:
        print("🎉 所有測試通過！數據庫功能正常")
    else:
        print("⚠️ 部分測試失敗，請檢查相關功能")
    
    # 清理測試數據庫
    cleanup_test_database()

if __name__ == "__main__":
    main()
