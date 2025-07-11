import os
import json
import logging
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes
)
from game_manager import GameManager

logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("BOT_TOKEN")

with open("roles.json", "r", encoding="utf-8") as f:
    ROLES = json.load(f)

game_manager = GameManager()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    gif_url = "https://media.giphy.com/media/6qbNRDTBpzmYChvX85/giphy.gif"
    caption = (
        f"Son bir Savaş istiyorum senden yeğen son bir savaş git onlara söyle olur mu, {user.first_name}.\n"
        "Emaneti olan Şehri Telegramı geri alacakmış de, de onlara olur mu.\n\n"
        "🎮 Eğlenceye katılmak için bota özelden /katil yaz ve oyuna dahil ol!"
    )
    keyboard = [
        [InlineKeyboardButton("🗡️ Katıl", url="https://t.me/ZeydOyunbot")],
        [InlineKeyboardButton("📜 Komutlar", callback_data="commands")],
        [InlineKeyboardButton("🎯 Oyun Hakkında", callback_data="about")],
        [InlineKeyboardButton("👥 Destek Grubu", url="https://t.me/Kizilsancaktr")],
        [InlineKeyboardButton("👤 Zeyd Bin Sabr", url="https://t.me/ZeydBinhalit")],
    ]
    await update.message.reply_animation(gif_url, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "commands":
        commands_text = (
            "📘 KOMUTLAR:\n\n"
            "/start – Botu başlat\n"
            "/savas – Grupta oyunu başlat\n"
            "/katil – Oyuna katıl (PM'den)\n"
            "/baris – Oyunu sonlandırır\n"
            "/roles – Ülkeleri ve güçlerini listeler\n"
        )
        await query.edit_message_text(commands_text)
    elif data == "about":
        about_text = (
            "Bu oyun bir dünya savaşı mizansenidir. Her oyuncu bir ülkeyi temsil eder.\n"
            "Amaç: Ayakta kalan son ülke olmak!\n\n"
            "🗳️ Güç kullanımı ve oylamalar PM'den yapılır.\n"
            "🎮 Katılmak için bota özelden yazın!"
        )
        await query.edit_message_text(about_text)

async def savas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if update.effective_chat.type == "private":
        await update.message.reply_text("⚠️ Oyun sadece grup sohbetlerinde başlatılabilir.")
        return
    started = game_manager.start_game(chat_id)
    if not started:
        await update.message.reply_text("⚔️ Oyun zaten başlatılmış!")
        return
    await update.message.reply_animation(
        animation="https://media4.giphy.com/media/14p5u4rpoC9Rm0/giphy.gif",
        caption="🎮 Oyun başladı! Katılmak için 👇 özelden /katil yaz\n⏳ Katılım süresi: 2 dakika."
    )

async def katil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = game_manager.get_last_group_chat_id()
    user = update.effective_user

    if update.effective_chat.type != "private":
        await update.message.reply_text("❗ Lütfen bu komutu özelden kullan.")
        return

    if not chat_id:
        await update.message.reply_text("🔍 Aktif bir oyun bulunamadı. Grup yöneticisi /savas komutunu kullanmalı.")
        return

    added = game_manager.add_player(chat_id, user.id, user.first_name)
    if added:
        await update.message.reply_text(f"✅ {user.first_name}, oyuna katıldınız!")
    else:
        await update.message.reply_text("🚫 Zaten katıldınız veya oyun başlamamış olabilir.")

async def baris(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in game_manager.active_games:
        del game_manager.active_games[chat_id]
        gif = "https://media1.giphy.com/media/BkKhrTlrf9dqolt80i/giphy.gif"
        await update.message.reply_animation(gif, caption="⚪ Korkaklar gibi kaçtılar, avratlar gibi savaştılar.\nBarışı seçtiler...")
    else:
        await update.message.reply_text("❌ Bu grupta aktif oyun yok.")

async def roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "🌍 ÜLKELER ve GÜÇLERİ:\n\n"
    for role in ROLES.values():
        msg += f"🔹 {role['name']} — {role['power_desc']}\n"
    await update.message.reply_text(msg)

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bilinmeyen komut. /start yazarak yeniden başlayabilirsiniz.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("savas", savas))
    app.add_handler(CommandHandler("katil", katil))
    app.add_handler(CommandHandler("baris", baris))
    app.add_handler(CommandHandler("roles", roles))

    app.add_handler(CallbackQueryHandler(callback_handler, pattern="^(commands|about)$"))
    app.add_handler(CommandHandler(None, unknown))

    app.run_polling()

if __name__ == "__main__":
    main()
