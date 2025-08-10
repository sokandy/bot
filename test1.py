from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = "7298343296:AAHYGrvh8up18Kmi6ibkl10aXbkegAJk_H8"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! 我是你的Bot。")

if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()