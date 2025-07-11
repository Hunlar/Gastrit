import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)
from dotenv import load_dotenv
from game_manager import GameManager

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

# Roller dosyasını yükle
with open("roles.json", "r", encoding="utf-8") as f:
    ROLES = json.load(f)

game_manager = GameManager()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gif_url = "https://media.giphy.com/media/6qbNRDTBpzmYChvX85/giphy.gif"
    user_name = update.effective_user.first_name
    start_text = (
        f"Son bir Savaş istiyorum senden yeğen son bir savaş git onlara söyle olur mu, {user_name}\n"
        "Emaneti olan Şehri Telegramı geri alacakmış de, de onlara olur mu.\n\n"
        "🎮 Eğlenceye katılmak için botu gruba ekle ve dostlarınla savaşı hisset!"
    )
    keyboard = [
        [InlineKeyboardButton("🎮 Komutlar", callback_data="commands")],
        [InlineKeyboardButton("📜 Oyun Hakkında", callback_data="about")],
        [InlineKeyboardButton("👥 Destek Grubu", url="https://t.me/Kizilsancaktr")],
        [InlineKeyboardButton("🧠 Zeyd Bin Sabr", url="https://t.me/ZeydBinhalit")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_animation(gif_url, caption=start_text, reply_markup=reply_markup)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "commands":
        commands_text = (
            "📜 /start : Botu başlatır\n"
            "⚔️ /savas : Gruba savaş başlatır\n"
            "🛑 /baris : Savaşı durdurur\n"
            "🏳️‍🌈 /roles : Ülke yeteneklerini gösterir\n"
        )
        await query.edit_message_text(commands_text)
    elif data == "about":
        about_text = (
            "Bu oyun bir dünya savaşı simülasyonudur.\n"
            "Ülke lideri olarak halkınızı yönetin ve savaşı kazanın!"
        )
        await query.edit_message_text(about_text)

async def savas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type != "group" and chat.type != "supergroup":
        await update.message.reply_text("Savaş yalnızca gruplarda başlatılabilir.")
        return

    chat_id = chat.id
    started = game_manager.start_game(chat_id)
    if started:
        gif = "https://media4.giphy.com/media/14p5u4rpoC9Rm0/giphy.gif"
        await update.message.reply_animation(gif, caption="⚔️ Savaş başladı! Katılmak için aşağıdaki butona basın.")
        keyboard = [
            [InlineKeyboardButton("🎮 Katıl", url="https://t.me/ZeydOyunbot?start=katil")],
        ]
        await update.message.reply_text("Oyuna katılmak için özelden start verin.", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("❗ Zaten bir savaş başlatılmış.")

async def baris(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in game_manager.active_games:
        del game_manager.active_games[chat_id]
        gif = "https://media1.giphy.com/media/BkKhrTlrf9dqolt80i/giphy.gif"
        await update.message.reply_animation(gif, caption="Korkaklar gibi kaçtılar, avratlar gibi savaştılar. Bu yüzden barışı seçtiler.")
    else:
        await update.message.reply_text("🔇 Aktif savaş yok.")

async def roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = "🌍 Ülkeler ve Güçleri:\n\n"
    for key, val in ROLES.items():
        message += f"• {val['name']}: {val['power_desc']}\n"
    await update.message.reply_text(message)

# Katılım (özel mesajda /start sonrası katılım kontrolü)
async def pm_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = game_manager.last_started_group
    user = update.effective_user
    added = game_manager.add_player(chat_id, user.id, user.first_name)
    if added:
        await update.message.reply_text(f"{user.first_name}, '{game_manager.group_name(chat_id)}' oyununa başarıyla katıldınız!")
    else:
        await update.message.reply_text("❗ Zaten katıldınız veya oyun başlamadı.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("savas", savas))
    app.add_handler(CommandHandler("baris", baris))
    app.add_handler(CommandHandler("roles", roles))

    # PM katılım özel start
    app.add_handler(CommandHandler("katil", pm_start))

    app.add_handler(CallbackQueryHandler(callback_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
