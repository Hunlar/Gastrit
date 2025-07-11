import os
import json
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)
from game_manager import GameManager

load_dotenv()
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("Bot token'ı ortam değişkeni olarak ayarlanmamış! Lütfen TOKEN olarak tanımlayın.")

logging.basicConfig(level=logging.INFO)
game_manager = GameManager()

with open("roles.json", "r", encoding="utf-8") as f:
    ROLES = json.load(f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gif_url = "https://media.giphy.com/media/6qbNRDTBpzmYChvX85/giphy.gif"
    user_name = update.effective_user.first_name
    start_text = (
        f"Son bir Savaş istiyorum senden yeğen son bir savaş git onlara söyle olur mu, {user_name} "
        "Emaneti olan Şehri Telegramı geri alacakmış de, de onlara olur mu.\n\n"
        "Eğlenceye katılmak için botu gruba ekle ve dostlarınla savaşı hisset!"
    )
    keyboard = [
        [InlineKeyboardButton("Komutlar", callback_data="commands")],
        [InlineKeyboardButton("Oyun Hakkında", callback_data="about")],
        [InlineKeyboardButton("Destek Grubu", url="https://t.me/Kizilsancaktr")],
        [InlineKeyboardButton("Zeyd Bin Sabr", url="https://t.me/ZeydBinhalit")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_animation(gif_url, caption=start_text, reply_markup=reply_markup)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "commands":
        text = (
            "/start - Botu başlatır\n"
            "/savas - Oyunu başlatır\n"
            "/katil - Oyuna katıl\n"
            "/baris - Oyunu bitirir\n"
            "/roles - Ülkeleri listeler\n"
            "/baslat - Katılım sonrası oyunu başlatır"
        )
        await query.edit_message_text(text)
    elif data == "about":
        roles_info = ""
        for role in ROLES.values():
            roles_info += f"• {role['name']}: {role['power_desc']}\n"
        await query.edit_message_text(f"🌍 Dünya Savaşı Simülasyonu 🌍\n\n{roles_info}")

async def savas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if update.effective_chat.type == "private":
        await update.message.reply_text("Oyun sadece grup sohbetinde başlatılabilir.")
        return

    started = game_manager.start_game(chat_id)
    if not started:
        await update.message.reply_text("Zaten bir oyun başlatılmış.")
        return

    keyboard = [
        [InlineKeyboardButton("Katıl", url=f"https://t.me/{context.bot.username}?start=katil")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_animation(
        animation="https://media4.giphy.com/media/14p5u4rpoC9Rm0/giphy.gif",
        caption="Oyun başladı! Katılmak için aşağıdaki butona tıklayın.",
        reply_markup=reply_markup
    )

async def katil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        await update.message.reply_text("Lütfen özelden katılmak için tıklayın.")
        return

    user = update.effective_user
    success = game_manager.add_player_to_latest_game(user.id, user.first_name)

    if success:
        await update.message.reply_text("Katıldınız! Grup sohbetine dönün.")
    else:
        await update.message.reply_text("Katılım başarısız. Oyun başlamamış olabilir.")

async def baris(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in game_manager.active_games:
        del game_manager.active_games[chat_id]
        gif_url = "https://media.giphy.com/media/BkKhrTlrf9dqolt80i/giphy.gif"
        await update.message.reply_animation(
            gif_url,
            caption="Korkaklar gibi kaçtılar avratlar gibi savaştılar bu yüzden barışı seçtiler."
        )
    else:
        await update.message.reply_text("Aktif bir oyun yok.")

async def roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = ""
    for role in ROLES.values():
        text += f"• {role['name']}: {role['power_desc']}\n"
    await update.message.reply_text(text)

async def baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    result = game_manager.begin_battle(chat_id)
    if result:
        await update.message.reply_text("Oyun başlıyor, roller dağıtılıyor...")
    else:
        await update.message.reply_text("Oyun başlatılamadı. Katılım yetersiz veya oyun yok.")

async def callback_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await game_manager.handle_callback(query)

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bilinmeyen komut. Lütfen /start ile başlayın.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("savas", savas))
    app.add_handler(CommandHandler("katil", katil))
    app.add_handler(CommandHandler("baris", baris))
    app.add_handler(CommandHandler("roles", roles))
    app.add_handler(CommandHandler("baslat", baslat))

    app.add_handler(CallbackQueryHandler(callback_handler, pattern="^(commands|about)$"))
    app.add_handler(CallbackQueryHandler(callback_game))

    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    app.run_polling()

if __name__ == "__main__":
    main()
