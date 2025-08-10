import sqlite3
import requests
import time
import threading
from datetime import datetime, timedelta
import asyncio
from telegram import Bot
import json

class StockMonitorDB:
    def __init__(self, db_path="stock_monitor.db", bot_token=None):
        self.db_path = db_path
        self.bot_token = bot_token
        self.bot = Bot(token=bot_token) if bot_token else None
        self.init_database()
        self.monitoring = False
        self.monitor_thread = None
        self.check_interval = 300  # 5分鐘檢查一次
    
    def init_database(self):
        """初始化數據庫和表結構"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 創建股票監控表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_watches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                target_price REAL NOT NULL,
                alert_type TEXT DEFAULT 'above',
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_alert TIMESTAMP DEFAULT NULL,
                alert_count INTEGER DEFAULT 0
            )
        ''')
        
        # 創建股票價格歷史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                volume INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 創建用戶設置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                chat_id INTEGER NOT NULL,
                check_interval INTEGER DEFAULT 300,
                timezone TEXT DEFAULT 'Asia/Hong_Kong',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"數據庫 {self.db_path} 初始化完成")
    
    def add_watch(self, user_id, chat_id, symbol, target_price, alert_type='above'):
        """添加股票監控"""
        try:
            # 處理香港股票代碼格式
            if symbol.endswith('.HK'):
                base_symbol = symbol.replace('.HK', '')
                if base_symbol.isdigit():
                    symbol = f"{base_symbol.zfill(4)}.HK"
            elif symbol.isdigit() and len(symbol) <= 4:
                symbol = f"{symbol.zfill(4)}.HK"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 檢查是否已存在相同的監控
            cursor.execute('''
                SELECT id FROM stock_watches 
                WHERE user_id = ? AND symbol = ? AND target_price = ? AND is_active = 1
            ''', (user_id, symbol, target_price))
            
            if cursor.fetchone():
                conn.close()
                return False, "此股票監控已存在"
            
            # 添加新的監控
            cursor.execute('''
                INSERT INTO stock_watches (user_id, chat_id, symbol, target_price, alert_type)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, chat_id, symbol, target_price, alert_type))
            
            watch_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return True, f"股票監控已添加 (ID: {watch_id})"
            
        except Exception as e:
            return False, f"添加監控失敗: {str(e)}"
    
    def remove_watch(self, user_id, watch_id):
        """移除股票監控"""
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
                return False, "找不到指定的監控或無權限移除"
                
        except Exception as e:
            return False, f"移除監控失敗: {str(e)}"
    
    def list_watches(self, user_id):
        """列出用戶的所有監控"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, symbol, target_price, alert_type, created_at, last_checked, alert_count
                FROM stock_watches 
                WHERE user_id = ? AND is_active = 1
                ORDER BY created_at DESC
            ''', (user_id,))
            
            watches = cursor.fetchall()
            conn.close()
            
            if not watches:
                return "您目前沒有設置任何股票監控"
            
            result = "📊 **您的股票監控列表**\n\n"
            for watch in watches:
                watch_id, symbol, target_price, alert_type, created_at, last_checked, alert_count = watch
                alert_text = "高於" if alert_type == 'above' else "低於"
                result += f"🆔 **ID: {watch_id}**\n"
                result += f"📈 股票: {symbol}\n"
                result += f"🎯 目標: {alert_text} ${target_price:.2f}\n"
                result += f"📅 創建: {created_at}\n"
                result += f"⏰ 最後檢查: {last_checked}\n"
                result += f"🚨 警報次數: {alert_count}\n\n"
            
            return result
            
        except Exception as e:
            return f"獲取監控列表失敗: {str(e)}"
    
    def get_stock_price(self, symbol):
        """獲取股票當前價格"""
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'chart' in data and 'result' in data['chart'] and data['chart']['result']:
                    result = data['chart']['result'][0]
                    meta = result['meta']
                    
                    current_price = meta.get('regularMarketPrice')
                    volume = meta.get('regularMarketVolume')
                    
                    if current_price:
                        # 保存價格歷史
                        self.save_price_history(symbol, current_price, volume)
                        return current_price, volume
            
            return None, None
            
        except Exception as e:
            print(f"獲取股票價格失敗 {symbol}: {str(e)}")
            return None, None
    
    def save_price_history(self, symbol, price, volume):
        """保存價格歷史到數據庫"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO price_history (symbol, price, volume)
                VALUES (?, ?, ?)
            ''', (symbol, price, volume))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"保存價格歷史失敗: {str(e)}")
    
    def check_alerts(self):
        """檢查所有監控並發送警報"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 獲取所有活躍的監控
            cursor.execute('''
                SELECT id, user_id, chat_id, symbol, target_price, alert_type, last_alert, alert_count
                FROM stock_watches 
                WHERE is_active = 1
            ''')
            
            watches = cursor.fetchall()
            conn.close()
            
            for watch in watches:
                watch_id, user_id, chat_id, symbol, target_price, alert_type, last_alert, alert_count = watch
                
                # 獲取當前價格
                current_price, volume = self.get_stock_price(symbol)
                
                if current_price is None:
                    continue
                
                # 檢查是否需要發送警報
                should_alert = False
                alert_message = ""
                
                if alert_type == 'above' and current_price >= target_price:
                    should_alert = True
                    alert_message = f"🚨 **股票警報** 🚨\n\n"
                    alert_message += f"📈 **{symbol}** 已達到目標價格！\n"
                    alert_message += f"🎯 目標價格: ${target_price:.2f}\n"
                    alert_message += f"💰 當前價格: ${current_price:.2f}\n"
                    alert_message += f"📊 成交量: {volume:,}" if volume else "📊 成交量: N/A"
                
                elif alert_type == 'below' and current_price <= target_price:
                    should_alert = True
                    alert_message = f"🚨 **股票警報** 🚨\n\n"
                    alert_message += f"📉 **{symbol}** 已跌至目標價格！\n"
                    alert_message += f"🎯 目標價格: ${target_price:.2f}\n"
                    alert_message += f"💰 當前價格: ${current_price:.2f}\n"
                    alert_message += f"📊 成交量: {volume:,}" if volume else "📊 成交量: N/A"
                
                # 發送警報
                if should_alert and self.bot:
                    try:
                        # 檢查是否在冷卻期內（避免重複警報）
                        if last_alert:
                            last_alert_time = datetime.fromisoformat(last_alert)
                            if datetime.now() - last_alert_time < timedelta(hours=1):
                                continue
                        
                        # 發送Telegram消息
                        asyncio.run(self.send_telegram_message(chat_id, alert_message))
                        
                        # 更新最後警報時間和警報次數
                        conn = sqlite3.connect(self.db_path)
                        cursor = conn.cursor()
                        cursor.execute('''
                            UPDATE stock_watches 
                            SET last_alert = CURRENT_TIMESTAMP, alert_count = alert_count + 1
                            WHERE id = ?
                        ''', (watch_id,))
                        conn.commit()
                        conn.close()
                        
                        print(f"已發送警報: {symbol} 達到目標價格 ${target_price}")
                        
                    except Exception as e:
                        print(f"發送警報失敗: {str(e)}")
                
                # 更新最後檢查時間
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE stock_watches 
                    SET last_checked = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (watch_id,))
                conn.commit()
                conn.close()
                
        except Exception as e:
            print(f"檢查警報失敗: {str(e)}")
    
    async def send_telegram_message(self, chat_id, message):
        """發送Telegram消息"""
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"發送Telegram消息失敗: {str(e)}")
    
    def start_monitoring(self, interval_seconds=None):
        """開始監控"""
        if self.monitoring:
            return False, "監控已在運行中"
        
        if interval_seconds:
            self.check_interval = interval_seconds
        
        self.monitoring = True
        
        def monitor_loop():
            while self.monitoring:
                try:
                    print(f"檢查股票警報... {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    self.check_alerts()
                    time.sleep(self.check_interval)
                except Exception as e:
                    print(f"監控循環錯誤: {str(e)}")
                    time.sleep(60)  # 錯誤時等待1分鐘
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        return True, f"股票監控已啟動，檢查間隔: {self.check_interval}秒"
    
    def stop_monitoring(self):
        """停止監控"""
        if not self.monitoring:
            return False, "監控未在運行"
        
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        return True, "股票監控已停止"
    
    def get_monitoring_status(self):
        """獲取監控狀態"""
        return {
            'is_monitoring': self.monitoring,
            'thread_alive': self.monitor_thread.is_alive() if self.monitor_thread else False,
            'check_interval': self.check_interval,
            'database_path': self.db_path
        }
    
    def get_statistics(self):
        """獲取監控統計信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 總監控數量
            cursor.execute('SELECT COUNT(*) FROM stock_watches WHERE is_active = 1')
            total_watches = cursor.fetchone()[0]
            
            # 今日警報數量
            today = datetime.now().date()
            cursor.execute('''
                SELECT COUNT(*) FROM stock_watches 
                WHERE is_active = 1 AND DATE(last_alert) = ?
            ''', (today,))
            today_alerts = cursor.fetchone()[0]
            
            # 總警報數量
            cursor.execute('SELECT SUM(alert_count) FROM stock_watches WHERE is_active = 1')
            total_alerts = cursor.fetchone()[0] or 0
            
            conn.close()
            
            return {
                'total_watches': total_watches,
                'today_alerts': today_alerts,
                'total_alerts': total_alerts,
                'monitoring_status': self.get_monitoring_status()
            }
            
        except Exception as e:
            return {'error': str(e)}

# 測試代碼
if __name__ == "__main__":
    # 創建監控實例
    monitor = StockMonitorDB()
    
    # 測試添加監控
    success, message = monitor.add_watch(
        user_id=12345,
        chat_id=12345,
        symbol="0005.HK",
        target_price=50.0,
        alert_type="above"
    )
    print(f"添加監控: {message}")
    
    # 列出監控
    watches = monitor.list_watches(12345)
    print(watches)
    
    # 獲取統計信息
    stats = monitor.get_statistics()
    print(f"統計信息: {json.dumps(stats, indent=2, default=str)}")
    
    # 啟動監控（測試模式，每30秒檢查一次）
    success, message = monitor.start_monitoring(interval_seconds=30)
    print(f"啟動監控: {message}")
    
    try:
        # 保持運行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop_monitoring()
        print("監控已停止")
