import json
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)
from game_manager import GameManager
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

with open("roles.json", "r", encoding="utf-8") as f:
    ROLES = json.load(f)

game_manager = GameManager()

# Start komutu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_type = update.effective_chat.type
    gif_url = "https://media.giphy.com/media/6qbNRDTBpzmYChvX85/giphy.gif"

    start_text = (
        f"Son bir Savaş istiyorum senden yeğen son bir savaş git onlara söyle olur mu, {user.first_name}\n"
        "Emaneti olan Şehri Telegramı geri alacakmış de, de onlara olur mu.\n\n"
        "🎮 Eğlenceye katılmak için botu gruba ekle ve dostlarınla savaşı hisset!"
    )

    keyboard = [
        [InlineKeyboardButton("Komutlar", callback_data="commands")],
        [InlineKeyboardButton("Oyun Hakkında", callback_data="about")],
        [InlineKeyboardButton("Destek Grubu", url="https://t.me/Kizilsancaktr")],
        [InlineKeyboardButton("Zeyd Bin Sabr", url="https://t.me/ZeydBinhalit")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if chat_type == "private":
        await update.message.reply_animation(gif_url, caption=start_text, reply_markup=reply_markup)
        # Katılmayı gruba yönlendir
        await update.message.reply_text("Bir oyuna katılmak için grup içindeki Katıl butonuna tıklamalısın.")
    else:
        await update.message.reply_text("Bot özel mesajda başlatılmalı.")

# Callback (buton) işlemleri
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "commands":
        text = (
            "/start - Botu başlatır\n"
            "/savas - Grupta oyunu başlatır\n"
            "/baris - Oyunu bitirir\n"
            "/roles - Ülke rollerini listeler"
        )
        await query.edit_message_text(text)
    elif data == "about":
        await query.edit_message_text(
            "Bu oyun bir dünya savaşı simülasyonudur. "
            "Ülke başkanı olarak strateji kur ve hayatta kal!"
        )
    elif data.startswith("katil_"):
        chat_id = int(data.split("_")[1])
        user = query.from_user
        joined = game_manager.add_player(chat_id, user.id, user.first_name)
        if joined:
            await query.edit_message_text(f"{user.first_name}, {chat_id} grubundaki oyuna katıldınız!")
        else:
            await query.edit_message_text("Zaten katıldınız veya oyun başladı.")

# /savas komutu grupta oyunu başlatır
async def savas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "group" and update.effective_chat.type != "supergroup":
        await update.message.reply_text("Sadece grup içinde başlatabilirsin.")
        return

    chat_id = update.effective_chat.id
    if not game_manager.start_game(chat_id):
        await update.message.reply_text("Zaten başlatılmış bir oyun var.")
        return

    gif = "https://media.giphy.com/media/14p5u4rpoC9Rm0/giphy.gif"
    await update.message.reply_animation(gif, caption="Oyun başladı! Katılmak için aşağıdaki butona tıklayın.")

    button = [
        [InlineKeyboardButton("Katıl", callback_data=f"katil_{chat_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(button)
    await context.bot.send_message(chat_id=chat_id, text="Katılmak için aşağıdaki butona tıklayın.", reply_markup=reply_markup)

# /baris komutu
async def baris(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if game_manager.end_game(chat_id):
        gif = "https://media.giphy.com/media/BkKhrTlrf9dqolt80i/giphy.gif"
        await update.message.reply_animation(gif, caption="Korkaklar gibi kaçtılar, barışı seçtiler.")
    else:
        await update.message.reply_text("Aktif oyun yok.")

# /roles komutu
async def roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "🗺️ Mevcut Ülkeler ve Güçleri:\n\n"
    for role in ROLES.values():
        msg += f"• {role['name']}: {role['power_desc']}\n"
    await update.message.reply_text(msg)

# Hatalı komutlar
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bilinmeyen komut. /start ile başlayabilirsin.")

# Başlatıcı
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("savas", savas))
    app.add_handler(CommandHandler("baris", baris))
    app.add_handler(CommandHandler("roles", roles))
    app.add_handler(CallbackQueryHandler(callback_handler))

    app.add_handler(CommandHandler("katil", unknown))  # Artık kullanılmıyor
    app.add_handler(CommandHandler("help", unknown))
    app.run_polling()

if __name__ == "__main__":
    main()
