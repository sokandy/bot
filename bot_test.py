from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import datetime
import requests
import json
import os

# 創建單一數據庫實例
try:
    from stock_monitor_db import StockMonitorDB
    monitor_db = StockMonitorDB()
    print("✅ 數據庫實例創建成功")
except ImportError:
    print("❌ 無法導入 StockMonitorDB 模塊")
    monitor_db = None
except Exception as e:
    print(f"❌ 數據庫初始化失敗: {e}")
    monitor_db = None

TOKEN = os.environ["BOT_TOKEN"]

# 當用戶輸入 /start 時觸發
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🕐 現在時間", callback_data='time')],
        [InlineKeyboardButton("🧮 計算器", callback_data='calculator')],
        [InlineKeyboardButton("🌤️ 天氣查詢", callback_data='weather')],
        [InlineKeyboardButton("📊 股票查詢", callback_data='stock')],
        [InlineKeyboardButton("📈 股票比較", callback_data='stockcompare')],
        [InlineKeyboardButton("📰 股票新聞", callback_data='stocknews')],
        [InlineKeyboardButton("❓ 幫助", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "你好！我是你的多功能 Telegram Bot！\n請選擇功能：",
        reply_markup=reply_markup
    )

# 當用戶輸入 /help 時觸發
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🤖 Bot 功能列表

基本指令:
/start - 開始使用機器人
/help - 顯示此幫助訊息
/time - 顯示現在時間
/calc <算式> - 計算數學算式 (例: /calc 2+3*4)
/weather <城市> - 查詢天氣 (例: /weather Hong Kong)

📊 股票功能:
/stock <代碼> - 查詢股票價格 (例: /stock AAPL 或 /stock 0005.HK)
/stockinfo <代碼> - 詳細股票資訊 (財務數據、P/E比率等) (例: /stockinfo 0005.HK)
/stocknews <代碼> - 股票相關新聞
/stockcompare <代碼1> <代碼2> - 股票比較 (例: /stockcompare AAPL MSFT)
/stockwatch <代碼> <價格> - 設置股票監控 (例: /stockwatch 0005.HK 50.0)
/watchlist - 查看監控列表
/removewatch <ID> - 移除監控 (例: /removewatch 1)

互動功能:
- 點擊下方按鈕使用功能
- 傳送文字訊息會得到回覆
- 支援數學計算、天氣查詢和完整股票分析
    """
    await update.message.reply_text(help_text)

# 當用戶輸入 /time 時觸發
async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now()
    time_str = now.strftime("%Y年%m月%d日 %H:%M:%S")
    await update.message.reply_text(f"🕐 現在時間：{time_str}")

# 當用戶輸入 /calc 時觸發
async def calc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        expression = ' '.join(context.args)
        if not expression:
            await update.message.reply_text("請輸入算式！例：/calc 2+3*4")
            return
        
        # 安全的數學計算
        allowed_chars = set('0123456789+-*/.() ')
        if not all(c in allowed_chars for c in expression):
            await update.message.reply_text("❌ 算式包含不安全的字符！")
            return
        
        result = eval(expression)
        await update.message.reply_text(f"🧮 計算結果：{expression} = {result}")
    except Exception as e:
        await update.message.reply_text(f"❌ 計算錯誤：{str(e)}")

# 當用戶輸入 /weather 時觸發
async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("請輸入城市名稱！例：/weather Hong Kong")
        return
    
    city = ' '.join(context.args)
    try:
        # 使用 OpenWeatherMap API (免費版)
        # 你需要註冊獲取 API key: https://openweathermap.org/api
        api_key = "9ffedf5725fcf3b1a942387eada4856a"  # 替換成你的 API key
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=zh_tw"
        
        response = requests.get(url)
        print(f"Weather API Response Status: {response.status_code}")
        print(f"Weather API Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            temp = data['main']['temp']
            humidity = data['main']['humidity']
            description = data['weather'][0]['description']
            
            weather_info = f"🌤️ {city} 天氣資訊\n"
            weather_info += f"🌡️ 溫度：{temp}°C\n"
            weather_info += f"💧 濕度：{humidity}%\n"
            weather_info += f"☁️ 天氣：{description}"
            
            await update.message.reply_text(weather_info)
        else:
            error_msg = f"❌ 無法獲取 {city} 的天氣資訊 (狀態碼: {response.status_code})"
            if response.status_code == 401:
                error_msg += "\n🔑 API Key 無效或已過期"
            elif response.status_code == 404:
                error_msg += "\n🏙️ 找不到該城市，請檢查城市名稱"
            elif response.status_code == 429:
                error_msg += "\n⏰ API 請求次數已達上限，請稍後再試"
            await update.message.reply_text(error_msg)
    except Exception as e:
        await update.message.reply_text(f"❌ 天氣查詢錯誤：{str(e)}")
        print(f"Weather API Exception: {e}")

# 當用戶輸入 /stock 時觸發
async def stock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("請輸入股票代碼！例：/stock AAPL 或 /stock 0700.HK")
        return
    
    symbol = ' '.join(context.args).upper()
    try:
        # 使用 Yahoo Finance API (免費版)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers)
        print(f"Stock API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if 'chart' in data and 'result' in data['chart'] and data['chart']['result']:
                result = data['chart']['result'][0]
                meta = result['meta']
                quote = result['indicators']['quote'][0]
                
                # 獲取股票信息
                current_price = meta.get('regularMarketPrice', 'N/A')
                previous_close = meta.get('previousClose', 'N/A')
                open_price = meta.get('regularMarketOpen', 'N/A')
                high = meta.get('regularMarketDayHigh', 'N/A')
                low = meta.get('regularMarketDayLow', 'N/A')
                volume = meta.get('regularMarketVolume', 'N/A')
                
                # 計算漲跌幅
                if current_price != 'N/A' and previous_close != 'N/A':
                    change = current_price - previous_close
                    change_percent = (change / previous_close) * 100
                    change_symbol = "📈" if change >= 0 else "📉"
                else:
                    change = 'N/A'
                    change_percent = 'N/A'
                    change_symbol = "📊"
                
                # 格式化價格
                def format_price(price):
                    if price == 'N/A':
                        return 'N/A'
                    return f"{price:.2f}"
                
                stock_info = f"📊 **{symbol} 股票資訊**\n\n"
                stock_info += f"💰 現價：{format_price(current_price)}\n"
                stock_info += f"{change_symbol} 漲跌：{format_price(change)} ({format_price(change_percent)}%)\n"
                stock_info += f"🔄 昨收：{format_price(previous_close)}\n"
                stock_info += f"🚪 開盤：{format_price(open_price)}\n"
                stock_info += f"⬆️ 最高：{format_price(high)}\n"
                stock_info += f"⬇️ 最低：{format_price(low)}\n"
                stock_info += f"📈 成交量：{volume:,}" if volume != 'N/A' else "📈 成交量：N/A"
                
                await update.message.reply_text(stock_info, parse_mode='Markdown')
            else:
                await update.message.reply_text(f"❌ 無法獲取 {symbol} 的股票資訊\n請檢查股票代碼是否正確")
        else:
            await update.message.reply_text(f"❌ 無法獲取 {symbol} 的股票資訊 (狀態碼: {response.status_code})")
    except Exception as e:
        await update.message.reply_text(f"❌ 股票查詢錯誤：{str(e)}")
        print(f"Stock API Exception: {e}")

# 當用戶輸入 /stockinfo 時觸發 - 詳細股票信息
async def stockinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("請輸入股票代碼！例：/stockinfo 0005.HK 或 /stockinfo AAPL")
        return
    
    symbol = ' '.join(context.args).upper()
    
    # 處理香港股票代碼格式
    if symbol.endswith('.HK'):
        # 確保是4位數字格式
        base_symbol = symbol.replace('.HK', '')
        if base_symbol.isdigit():
            symbol = f"{base_symbol.zfill(4)}.HK"
    elif symbol.isdigit() and len(symbol) <= 4:
        # 如果是純數字，自動添加.HK後綴
        symbol = f"{symbol.zfill(4)}.HK"
    
    try:
        # 首先嘗試獲取基本股票信息
        basic_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        basic_response = requests.get(basic_url, headers=headers)
        
        if basic_response.status_code == 200:
            basic_data = basic_response.json()
            if 'chart' in basic_data and 'result' in basic_data['chart'] and basic_data['chart']['result']:
                result = basic_data['chart']['result'][0]
                meta = result['meta']
                
                # 獲取基本價格信息
                current_price = meta.get('regularMarketPrice', 'N/A')
                previous_close = meta.get('previousClose', 'N/A')
                open_price = meta.get('regularMarketOpen', 'N/A')
                high = meta.get('regularMarketDayHigh', 'N/A')
                low = meta.get('regularMarketDayLow', 'N/A')
                volume = meta.get('regularMarketVolume', 'N/A')
                
                # 計算漲跌幅
                if current_price != 'N/A' and previous_close != 'N/A':
                    change = current_price - previous_close
                    change_percent = (change / previous_close) * 100
                    change_symbol = "📈" if change >= 0 else "📉"
                else:
                    change = 'N/A'
                    change_percent = 'N/A'
                    change_symbol = "📊"
                
                # 格式化價格
                def format_price(price):
                    if price == 'N/A':
                        return 'N/A'
                    return f"{price:.2f}"
                
                # 構建基本信息
                info_text = f"📊 **{symbol} 股票資訊**\n\n"
                info_text += f"💰 現價：{format_price(current_price)}\n"
                info_text += f"{change_symbol} 漲跌：{format_price(change)} ({format_price(change_percent)}%)\n"
                info_text += f"🔄 昨收：{format_price(previous_close)}\n"
                info_text += f"🚪 開盤：{format_price(open_price)}\n"
                info_text += f"⬆️ 最高：{format_price(high)}\n"
                info_text += f"⬇️ 最低：{format_price(low)}\n"
                info_text += f"📈 成交量：{volume:,}" if volume != 'N/A' else "📈 成交量：N/A"
                
                # 嘗試獲取詳細財務數據
                try:
                    detail_url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}?modules=summaryDetail,financialData,defaultKeyStatistics"
                    detail_response = requests.get(detail_url, headers=headers)
                    
                    if detail_response.status_code == 200:
                        detail_data = detail_response.json()
                        quote_summary = detail_data.get('quoteSummary', {}).get('result', [{}])[0]
                        
                        # 基本財務數據
                        if 'financialData' in quote_summary:
                            financial = quote_summary['financialData']
                            info_text += "\n\n💰 **財務數據**\n"
                            
                            market_cap = financial.get('marketCap')
                            if market_cap:
                                if market_cap >= 1e12:
                                    info_text += f"市值：${market_cap/1e12:.2f}T\n"
                                elif market_cap >= 1e9:
                                    info_text += f"市值：${market_cap/1e9:.2f}B\n"
                                elif market_cap >= 1e6:
                                    info_text += f"市值：${market_cap/1e6:.2f}M\n"
                                else:
                                    info_text += f"市值：${market_cap:,.0f}\n"
                            else:
                                info_text += "市值：N/A\n"
                            
                            forward_pe = financial.get('forwardPE')
                            if forward_pe:
                                info_text += f"P/E比率：{forward_pe:.2f}\n"
                            else:
                                info_text += "P/E比率：N/A\n"
                            
                            roe = financial.get('returnOnEquity')
                            if roe:
                                info_text += f"ROE：{roe:.2%}\n"
                            else:
                                info_text += "ROE：N/A\n"
                            
                            debt_to_equity = financial.get('debtToEquity')
                            if debt_to_equity:
                                info_text += f"債務權益比：{debt_to_equity:.2f}\n"
                            else:
                                info_text += "債務權益比：N/A\n"
                        
                        # 交易統計
                        if 'summaryDetail' in quote_summary:
                            summary = quote_summary['summaryDetail']
                            info_text += "\n📈 **交易統計**\n"
                            
                            fifty_two_week_high = summary.get('fiftyTwoWeekHigh')
                            if fifty_two_week_high:
                                info_text += f"52週高：{fifty_two_week_high:.2f}\n"
                            else:
                                info_text += "52週高：N/A\n"
                            
                            fifty_two_week_low = summary.get('fiftyTwoWeekLow')
                            if fifty_two_week_low:
                                info_text += f"52週低：{fifty_two_week_low:.2f}\n"
                            else:
                                info_text += "52週低：N/A\n"
                            
                            avg_volume = summary.get('averageVolume')
                            if avg_volume:
                                info_text += f"平均成交量：{avg_volume:,}\n"
                            else:
                                info_text += "平均成交量：N/A\n"
                            
                            dividend_yield = summary.get('dividendYield')
                            if dividend_yield:
                                info_text += f"股息收益率：{dividend_yield:.2%}\n"
                            else:
                                info_text += "股息收益率：N/A\n"
                    
                except Exception as detail_e:
                    print(f"Detail API Exception: {detail_e}")
                    info_text += "\n\n⚠️ 無法獲取詳細財務數據，僅顯示基本價格信息"
                
                await update.message.reply_text(info_text, parse_mode='Markdown')
            else:
                await update.message.reply_text(f"❌ 無法獲取 {symbol} 的股票資訊\n請檢查股票代碼是否正確")
        else:
            await update.message.reply_text(f"❌ 無法獲取 {symbol} 的股票資訊 (狀態碼: {basic_response.status_code})")
    except Exception as e:
        await update.message.reply_text(f"❌ 詳細資訊查詢錯誤：{str(e)}")
        print(f"Stockinfo API Exception: {e}")

# 當用戶輸入 /stocknews 時觸發 - 股票相關新聞
async def stocknews_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("請輸入股票代碼！例：/stocknews AAPL")
        return
    
    symbol = ' '.join(context.args).upper()
    try:
        # 獲取股票相關新聞
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if 'chart' in data and 'result' in data['chart'] and data['chart']['result']:
                result = data['chart']['result'][0]
                news = result.get('news', [])
                
                if news:
                    news_text = f"📰 **{symbol} 相關新聞**\n\n"
                    for i, article in enumerate(news[:5], 1):  # 顯示前5條新聞
                        title = article.get('title', '無標題')
                        source = article.get('source', '未知來源')
                        time = article.get('providerPublishTime', 0)
                        if time:
                            from datetime import datetime
                            news_time = datetime.fromtimestamp(time).strftime('%m-%d %H:%M')
                        else:
                            news_time = '未知時間'
                        
                        news_text += f"{i}. **{title}**\n"
                        news_text += f"   來源：{source} | {news_time}\n\n"
                    
                    await update.message.reply_text(news_text, parse_mode='Markdown')
                else:
                    await update.message.reply_text(f"📰 目前沒有 {symbol} 的相關新聞")
            else:
                await update.message.reply_text(f"❌ 無法獲取 {symbol} 的新聞")
        else:
            await update.message.reply_text(f"❌ 無法獲取 {symbol} 的新聞")
    except Exception as e:
        await update.message.reply_text(f"❌ 新聞查詢錯誤：{str(e)}")

# 當用戶輸入 /stockcompare 時觸發 - 股票比較
async def stockcompare_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("請輸入至少兩個股票代碼進行比較！例：/stockcompare AAPL MSFT")
        return
    
    symbols = [arg.upper() for arg in context.args[:5]]  # 最多比較5個股票
    try:
        compare_text = f"📊 **股票比較** ({', '.join(symbols)})\n\n"
        
        for symbol in symbols:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if 'chart' in data and 'result' in data['chart'] and data['chart']['result']:
                    result = data['chart']['result'][0]
                    meta = result['meta']
                    
                    current_price = meta.get('regularMarketPrice', 'N/A')
                    previous_close = meta.get('previousClose', 'N/A')
                    
                    if current_price != 'N/A' and previous_close != 'N/A':
                        change_percent = ((current_price - previous_close) / previous_close) * 100
                        change_symbol = "📈" if change_percent >= 0 else "📉"
                        compare_text += f"{change_symbol} **{symbol}**: ${current_price:.2f} ({change_percent:+.2f}%)\n"
                    else:
                        compare_text += f"📊 **{symbol}**: 數據不可用\n"
                else:
                    compare_text += f"❌ **{symbol}**: 無法獲取數據\n"
            else:
                compare_text += f"❌ **{symbol}**: 請求失敗\n"
        
        await update.message.reply_text(compare_text, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ 股票比較錯誤：{str(e)}")

# 當用戶輸入 /stockwatch 時觸發 - 設置股票監控
async def stockwatch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("請輸入股票代碼和目標價格！例：/stockwatch 0005.HK 50.0")
        return
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    symbol = context.args[0].upper()
    try:
        target_price = float(context.args[1])
        
        # 處理香港股票代碼格式
        if symbol.endswith('.HK'):
            base_symbol = symbol.replace('.HK', '')
            if base_symbol.isdigit():
                symbol = f"{base_symbol.zfill(4)}.HK"
        elif symbol.isdigit() and len(symbol) <= 4:
            symbol = f"{symbol.zfill(4)}.HK"
        
        # 嘗試獲取當前價格進行比較
        got_current_price = False
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if 'chart' in data and 'result' in data['chart'] and data['chart']['result']:
                    result = data['chart']['result'][0]
                    meta = result['meta']
                    current_price = meta.get('regularMarketPrice')
                    
                    if current_price:
                        change = current_price - target_price
                        change_percent = (change / target_price) * 100
                        status_emoji = "📈" if change >= 0 else "📉"
                        
                        watch_text = f"👀 **股票監控設置**\n\n"
                        watch_text += f"📈 股票：{symbol}\n"
                        watch_text += f"🎯 目標價格：${target_price:.2f}\n"
                        watch_text += f"💰 當前價格：${current_price:.2f}\n"
                        watch_text += f"{status_emoji} 差距：${change:.2f} ({change_percent:+.2f}%)\n"
                        watch_text += f"✅ 狀態：監控已設置\n\n"
                        watch_text += "💡 提示：此監控已記錄，當股票達到目標價格時會通知您"
                        got_current_price = True
        except:
            pass
        
        # 如果無法獲取當前價格，顯示基本信息
        if not got_current_price:
            watch_text = f"👀 **股票監控設置**\n\n"
            watch_text += f"📈 股票：{symbol}\n"
            watch_text += f"🎯 目標價格：${target_price:.2f}\n"
        
        # 嘗試保存到數據庫
        try:
            if monitor_db is None:
                watch_text += f"⚠️ 狀態：數據庫模塊未找到\n\n"
                watch_text += "💡 提示：請確保 stock_monitor_db.py 文件存在"
                await update.message.reply_text(watch_text, parse_mode='Markdown')
                return
            
            success, message = monitor_db.add_watch(user_id, chat_id, symbol, target_price)
            
            if success:
                watch_text += f"✅ 狀態：監控已保存到數據庫\n"
                watch_text += f"📝 信息：{message}\n\n"
                watch_text += "🔔 當股票價格達到目標時，您將收到通知！"
            else:
                watch_text += f"⚠️ 狀態：監控設置成功但數據庫保存失敗\n"
                watch_text += f"📝 信息：{message}\n\n"
                watch_text += "💡 提示：監控功能可能無法正常工作"
        except ImportError:
            watch_text += f"⚠️ 狀態：監控設置成功但數據庫模塊未找到\n\n"
            watch_text += "💡 提示：請確保 stock_monitor_db.py 文件存在"
        except Exception as db_error:
            watch_text += f"⚠️ 狀態：監控設置成功但數據庫保存失敗\n"
            watch_text += f"📝 錯誤：{str(db_error)}\n\n"
            watch_text += "💡 提示：監控功能可能無法正常工作"
        
        await update.message.reply_text(watch_text, parse_mode='Markdown')
        
    except ValueError:
        await update.message.reply_text("❌ 請輸入有效的目標價格！例：/stockwatch 0005.HK 50.0")
    except Exception as e:
        await update.message.reply_text(f"❌ 監控設置錯誤：{str(e)}")

# 當用戶輸入 /watchlist 時觸發 - 查看監控列表
async def watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    try:
        # 嘗試從數據庫獲取監控列表
        try:
            if monitor_db is None:
                watch_text = "📊 **您的股票監控列表**\n\n"
                watch_text += "❌ 數據庫模塊未找到，無法顯示真實監控列表\n\n"
                watch_text += "📋 可用的監控命令：\n"
                watch_text += "• /stockwatch <股票代碼> <目標價格> - 設置監控\n"
                watch_text += "• /removewatch <監控ID> - 移除監控\n"
                watch_text += "• /watchlist - 查看監控列表\n\n"
                watch_text += "📈 示例：\n"
                watch_text += "• /stockwatch 0005.HK 50.0\n"
                watch_text += "• /stockwatch 0700.HK 300.0\n"
                watch_text += "• /stockwatch AAPL 150.0"
                await update.message.reply_text(watch_text, parse_mode='Markdown')
                return
            
            watches = monitor_db.list_watches(user_id)
            
            if isinstance(watches, str) and "沒有設置任何監控" in watches:
                watch_text = "📊 **您的股票監控列表**\n\n"
                watch_text += "📭 目前沒有設置任何股票監控\n\n"
                watch_text += "📋 可用的監控命令：\n"
                watch_text += "• /stockwatch <股票代碼> <目標價格> - 設置監控\n"
                watch_text += "• /removewatch <監控ID> - 移除監控\n"
                watch_text += "• /watchlist - 查看監控列表\n\n"
                watch_text += "📈 示例：\n"
                watch_text += "• /stockwatch 0005.HK 50.0\n"
                watch_text += "• /stockwatch 0700.HK 300.0\n"
                watch_text += "• /stockwatch AAPL 150.0"
            else:
                watch_text = watches
        except ImportError:
            watch_text = "📊 **您的股票監控列表**\n\n"
            watch_text += "❌ 數據庫模塊未找到，無法顯示真實監控列表\n\n"
            watch_text += "📋 可用的監控命令：\n"
            watch_text += "• /stockwatch <股票代碼> <目標價格> - 設置監控\n"
            watch_text += "• /removewatch <監控ID> - 移除監控\n"
            watch_text += "• /watchlist - 查看監控列表\n\n"
            watch_text += "📈 示例：\n"
            watch_text += "• /stockwatch 0005.HK 50.0\n"
            watch_text += "• /stockwatch 0700.HK 300.0\n"
            watch_text += "• /stockwatch AAPL 150.0"
        except Exception as db_error:
            watch_text = "📊 **您的股票監控列表**\n\n"
            watch_text += f"❌ 數據庫操作失敗：{str(db_error)}\n\n"
            watch_text += "📋 可用的監控命令：\n"
            watch_text += "• /stockwatch <股票代碼> <目標價格> - 設置監控\n"
            watch_text += "• /removewatch <監控ID> - 移除監控\n"
            watch_text += "• /watchlist - 查看監控列表\n\n"
            watch_text += "📈 示例：\n"
            watch_text += "• /stockwatch 0005.HK 50.0\n"
            watch_text += "• /stockwatch 0700.HK 300.0\n"
            watch_text += "• /stockwatch AAPL 150.0"
        
        await update.message.reply_text(watch_text, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ 獲取監控列表失敗：{str(e)}")

# 當用戶輸入 /removewatch 時觸發 - 移除監控
async def removewatch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("請輸入監控ID！例：/removewatch 1")
        return
    
    try:
        watch_id = int(context.args[0])
        
        user_id = update.effective_user.id
        
        # 嘗試從數據庫移除監控
        try:
            if monitor_db is None:
                remove_text = f"🗑️ **移除股票監控**\n\n"
                remove_text += f"🆔 監控ID：{watch_id}\n"
                remove_text += f"⚠️ 狀態：數據庫模塊未找到\n\n"
                remove_text += "💡 提示：請確保 stock_monitor_db.py 文件存在"
                await update.message.reply_text(remove_text, parse_mode='Markdown')
                return
            
            success, message = monitor_db.remove_watch(user_id, watch_id)
            
            if success:
                remove_text = f"🗑️ **移除股票監控成功**\n\n"
                remove_text += f"🆔 監控ID：{watch_id}\n"
                remove_text += f"✅ 狀態：{message}\n\n"
                remove_text += "📝 監控已從數據庫中移除"
            else:
                remove_text = f"❌ **移除股票監控失敗**\n\n"
                remove_text += f"🆔 監控ID：{watch_id}\n"
                remove_text += f"❌ 狀態：{message}\n\n"
                remove_text += "💡 提示：請檢查監控ID是否正確"
        except ImportError:
            remove_text = f"🗑️ **移除股票監控**\n\n"
            remove_text += f"🆔 監控ID：{watch_id}\n"
            remove_text += f"⚠️ 狀態：數據庫模塊未找到\n\n"
            remove_text += "💡 提示：請確保 stock_monitor_db.py 文件存在"
        except Exception as db_error:
            remove_text = f"🗑️ **移除股票監控**\n\n"
            remove_text += f"🆔 監控ID：{watch_id}\n"
            remove_text += f"❌ 狀態：數據庫操作失敗\n"
            remove_text += f"📝 錯誤：{str(db_error)}\n\n"
            remove_text += "💡 提示：請稍後再試"
        
        await update.message.reply_text(remove_text, parse_mode='Markdown')
        
    except ValueError:
        await update.message.reply_text("❌ 請輸入有效的監控ID！例：/removewatch 1")
    except Exception as e:
        await update.message.reply_text(f"❌ 移除監控失敗：{str(e)}")

# 處理按鈕回調
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'time':
        now = datetime.datetime.now()
        time_str = now.strftime("%Y年%m月%d日 %H:%M:%S")
        await query.edit_message_text(f"🕐 現在時間：{time_str}")
    
    elif query.data == 'calculator':
        await query.edit_message_text("🧮 請使用 /calc 指令來計算算式\n例：/calc 2+3*4")
    
    elif query.data == 'weather':
        await query.edit_message_text("🌤️ 請使用 /weather 指令來查詢天氣\n例：/weather Hong Kong")
    
    elif query.data == 'stock':
        await query.edit_message_text("📊 請使用 /stock 指令來查詢股票價格\n例：/stock AAPL 或 /stock 0005.HK")
    
    elif query.data == 'stockcompare':
        await query.edit_message_text("📈 請使用 /stockcompare 指令來比較股票\n例：/stockcompare AAPL MSFT GOOGL")
    
    elif query.data == 'stocknews':
        await query.edit_message_text("📰 請使用 /stocknews 指令來查詢股票新聞\n例：/stocknews AAPL")
    
    elif query.data == 'help':
        await query.edit_message_text("❓ 請使用 /help 指令來查看完整幫助")

# 當用戶傳送普通訊息時觸發
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    # 檢查是否為數學算式
    if any(op in user_text for op in ['+', '-', '*', '/', '=']):
        try:
            # 移除等號並計算
            expression = user_text.replace('=', '').strip()
            allowed_chars = set('0123456789+-*/.() ')
            if all(c in allowed_chars for c in expression):
                result = eval(expression)
                await update.message.reply_text(f"🧮 計算結果：{expression} = {result}")
                return
        except:
            pass
    
    await update.message.reply_text(f"你說了: {user_text}")

if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()
    
    # 註冊指令和訊息處理器
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("time", time_command))
    app.add_handler(CommandHandler("calc", calc_command))
    app.add_handler(CommandHandler("weather", weather_command))
    app.add_handler(CommandHandler("stock", stock_command))
    app.add_handler(CommandHandler("stockinfo", stockinfo_command))
    app.add_handler(CommandHandler("stocknews", stocknews_command))
    app.add_handler(CommandHandler("stockcompare", stockcompare_command))
    app.add_handler(CommandHandler("stockwatch", stockwatch_command))
    app.add_handler(CommandHandler("watchlist", watchlist_command))
    app.add_handler(CommandHandler("removewatch", removewatch_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    print("Bot 運行中...")
    app.run_polling()  # 持續監聽新訊息
