import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from game_manager import GameManager
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
game_manager = GameManager()

# Roller yükleniyor
with open("roles.json", "r", encoding="utf-8") as f:
    ROLES = json.load(f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gif_url = "https://media.giphy.com/media/6qbNRDTBpzmYChvX85/giphy.gif"
    user_name = update.effective_user.first_name
    caption = (
        f"Son bir Savaş istiyorum senden yeğen son bir savaş git onlara söyle olur mu, {user_name} "
        "Emaneti olan Şehri Telegramı geri alacakmış de, de onlara olur mu.\n\n"
        "Eğlenceye katılmak için botu gruba ekle ve dostlarınla savaşı hisset!"
    )
    buttons = [
        [InlineKeyboardButton("Komutlar", callback_data="commands")],
        [InlineKeyboardButton("Oyun Hakkında", callback_data="about")],
        [InlineKeyboardButton("Destek Grubu", url="https://t.me/Kizilsancaktr")],
        [InlineKeyboardButton("Zeyd Bin Sabr", url="https://t.me/ZeydBinhalit")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_animation(animation=gif_url, caption=caption, reply_markup=reply_markup)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "commands":
        commands = (
            "/start – Botu başlatır\n"
            "/savas – Oyunu başlatır\n"
            "/katil – PM üzerinden oyuna katılım sağlar\n"
            "/baslat – Katılan oyuncularla oyunu başlatır\n"
            "/baris – Oyunu iptal eder\n"
            "/roles – Tüm ülkeleri listeler\n"
        )
        await query.edit_message_text(commands)
    elif data == "about":
        about = (
            "Bu oyun bir dünya savaşı simülasyonudur. Devlet başkanı olarak halkınızı yönlendirin!"
        )
        await query.edit_message_text(about)

async def savas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "group" and update.effective_chat.type != "supergroup":
        await update.message.reply_text("Sadece grupta kullanılabilir.")
        return

    started = game_manager.start_game(update.effective_chat.id)
    if not started:
        await update.message.reply_text("Oyun zaten başlatıldı.")
        return

    gif = "https://media4.giphy.com/media/14p5u4rpoC9Rm0/giphy.gif"
    button = InlineKeyboardMarkup([
        [InlineKeyboardButton("Katıl", url="https://t.me/ZeydOyunbot?start=katil")]
    ])
    await update.message.reply_animation(gif, caption="Savaş Başladı! PM'den katıl.", reply_markup=button)

async def katil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        await update.message.reply_text("Bu komutu sadece özelde kullanabilirsin.")
        return

    args = context.args
    if args and args[0] == "katil":
        joined = game_manager.add_player_from_pm(update.effective_user)
        if joined:
            await update.message.reply_text("Grup oyununa başarıyla katıldınız.")
        else:
            await update.message.reply_text("Zaten katıldınız veya aktif bir oyun yok.")
    else:
        await update.message.reply_text("Aktif bir oyuna katılmak için grup başlatmalı.")

async def baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if game_manager.can_start_game(chat_id):
        game_manager.assign_roles(chat_id)
        await update.message.reply_text("Oyun başlatıldı. Roller DM'den gönderildi.")
        await game_manager.send_roles_to_players(context)
    else:
        await update.message.reply_text("Katılım yetersiz veya oyun başlamamış.")

async def baris(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if game_manager.cancel_game(chat_id):
        gif = "https://media1.giphy.com/media/BkKhrTlrf9dqolt80i/giphy.gif"
        await update.message.reply_animation(gif, caption="Korkaklar gibi kaçtılar, barışı seçtiler.")
    else:
        await update.message.reply_text("Aktif oyun bulunamadı.")

async def roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "🗺 Ülkeler ve Özellikleri:\n\n"
    for key, role in ROLES.items():
        msg += f"• {role['name']}: {role['power_desc']}\n"
    await update.message.reply_text(msg)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("savas", savas))
    app.add_handler(CommandHandler("katil", katil))
    app.add_handler(CommandHandler("baslat", baslat))
    app.add_handler(CommandHandler("baris", baris))
    app.add_handler(CommandHandler("roles", roles))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
