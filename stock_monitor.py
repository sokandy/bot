import sqlite3
import requests
import time
import threading
from datetime import datetime

class StockMonitor:
    def __init__(self, db_path="stock_monitor.db"):
        self.db_path = db_path
        self.init_database()
        self.monitoring = False
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_watches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                target_price REAL NOT NULL,
                alert_type TEXT DEFAULT 'above',
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_watch(self, user_id, chat_id, symbol, target_price, alert_type='above'):
        try:
            if symbol.endswith('.HK'):
                base_symbol = symbol.replace('.HK', '')
                if base_symbol.isdigit():
                    symbol = f"{base_symbol.zfill(4)}.HK"
            elif symbol.isdigit() and len(symbol) <= 4:
                symbol = f"{symbol.zfill(4)}.HK"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO stock_watches (user_id, chat_id, symbol, target_price, alert_type)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, chat_id, symbol, target_price, alert_type))
            
            watch_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return True, f"監控已添加 (ID: {watch_id})"
            
        except Exception as e:
            return False, f"添加失敗: {str(e)}"
    
    def list_watches(self, user_id):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, symbol, target_price, alert_type, created_at
                FROM stock_watches 
                WHERE user_id = ? AND is_active = 1
            ''', (user_id,))
            
            watches = cursor.fetchall()
            conn.close()
            
            if not watches:
                return "沒有設置任何監控"
            
            result = "📊 **股票監控列表**\n\n"
            for watch in watches:
                watch_id, symbol, target_price, alert_type, created_at = watch
                alert_text = "高於" if alert_type == 'above' else "低於"
                result += f"🆔 ID: {watch_id}\n"
                result += f"📈 股票: {symbol}\n"
                result += f"🎯 目標: {alert_text} ${target_price:.2f}\n"
                result += f"📅 創建: {created_at}\n\n"
            
            return result
            
        except Exception as e:
            return f"獲取失敗: {str(e)}"
    
    def remove_watch(self, user_id, watch_id):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE stock_watches SET is_active = 0 
                WHERE id = ? AND user_id = ?
            ''', (watch_id, user_id))
            
            if cursor.rowcount > 0:
                conn.commit()
                conn.close()
                return True, "監控已移除"
            else:
                conn.close()
                return False, "找不到監控"
                
        except Exception as e:
            return False, f"移除失敗: {str(e)}"
    
    def get_stock_price(self, symbol):
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'chart' in data and 'result' in data['chart'] and data['chart']['result']:
                    result = data['chart']['result'][0]
                    meta = result['meta']
                    return meta.get('regularMarketPrice')
            
            return None
            
        except Exception as e:
            print(f"獲取價格失敗 {symbol}: {str(e)}")
            return None
