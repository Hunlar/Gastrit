import os
import json
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)
from game_manager import GameManager

load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("Bot token'ı ortam değişkeni olarak ayarlanmamış! Lütfen .env dosyasına TOKEN=... ekleyin.")

logging.basicConfig(level=logging.INFO)
game_manager = GameManager()

# Roller dosyasını yükle
with open("roles.json", "r", encoding="utf-8") as f:
    ROLES = json.load(f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gif_url = "https://media.giphy.com/media/6qbNRDTBpzmYChvX85/giphy.gif"
    user_name = update.effective_user.first_name
    start_text = (
        f"Son bir Savaş istiyorum senden yeğen, {user_name}!\n"
        "Emaneti olan Şehri Telegramı geri alacakmış de, de onlara olur mu.\n\n"
        "Aşağıdaki butonlarla oyuna katılabilir, bilgi alabilir veya destek alabilirsin."
    )

    keyboard = [
        [InlineKeyboardButton("Katıl", callback_data="katil")],
        [InlineKeyboardButton("Komutlar", callback_data="commands")],
        [InlineKeyboardButton("Oyun Hakkında", callback_data="about")],
        [InlineKeyboardButton("Destek Grubu", url="https://t.me/Kizilsancaktr")],
        [InlineKeyboardButton("Zeyd Bin Sabr", url="https://t.me/ZeydBinhalit")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_animation(gif_url, caption=start_text, reply_markup=reply_markup)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = query.from_user
    await query.answer()

    if data == "commands":
        commands_text = (
            "/start – Botu başlatır\n"
            "/savas – Gruba oyun kurar (Admin)\n"
            "/baslat – Katılanlarla oyunu başlatır\n"
            "/baris – Oyunu iptal eder\n"
            "/roles – Ülkeleri listeler\n"
        )
        await query.edit_message_text(commands_text)

    elif data == "about":
        about_text = "Bu oyun bir mizahi savaş simülasyonudur. Ülkeni temsil et, güç kullan, düşmanlarını ele!"
        await query.edit_message_text(about_text)

    elif data == "katil":
        chat_id = update.effective_user.id
        group_id = context.chat_data.get("group_id")
        if not group_id:
            await query.edit_message_text("Henüz aktif bir oyun başlatılmadı. Grup üzerinden /savas komutunu kullanın.")
            return

        added = game_manager.add_player(group_id, user.id, user.first_name)
        if added:
            await query.edit_message_text(f"{user.first_name}, **{group_id}** adlı gruptaki oyuna başarıyla katıldınız!")
        else:
            await query.edit_message_text("Zaten katıldınız ya da oyun çoktan başladı.")

async def savas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if update.effective_chat.type == "private":
        await update.message.reply_text("Oyun sadece grup sohbetlerinde başlatılabilir.")
        return

    started = game_manager.start_game(chat_id)
    if not started:
        await update.message.reply_text("Bu grupta oyun zaten başlatılmış.")
        return

    context.chat_data["group_id"] = chat_id
    await update.message.reply_text("Oyun başladı! Oyuncuların botla özelden konuşarak 'Katıl' butonuna basması gerekiyor.\nSüre: 2 dakika")

async def baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in game_manager.active_games:
        await update.message.reply_text("Henüz bir oyun başlatılmadı.")
        return

    assigned = game_manager.assign_roles(chat_id)
    if not assigned:
        await update.message.reply_text("Rol dağıtımı başarısız.")
        return

    await update.message.reply_text("Oyun resmen başladı! Roller dağıtıldı, güçler aktif.")
    # DM'den roller gönderilebilir (isteğe bağlı)

async def baris(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in game_manager.active_games:
        del game_manager.active_games[chat_id]
        gif_url = "https://media.giphy.com/media/BkKhrTlrf9dqolt80i/giphy.gif"
        await update.message.reply_animation(gif_url, caption="Barış yapıldı, oyun sona erdi.")
    else:
        await update.message.reply_text("Aktif bir oyun yok.")

async def roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "**Ülkeler ve Güçleri:**\n\n"
    for val in ROLES.values():
        msg += f"• {val['name']}: {val['power_desc']}\n"
    await update.message.reply_text(msg)

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bilinmeyen komut. Lütfen /start ile başlayın.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("savas", savas))
    app.add_handler(CommandHandler("baslat", baslat))
    app.add_handler(CommandHandler("baris", baris))
    app.add_handler(CommandHandler("roles", roles))
    app.add_handler(CallbackQueryHandler(callback_handler, pattern="^(commands|about|katil)$"))
    app.add_handler(CallbackQueryHandler(game_manager.handle_callback))

    app.run_polling()

if __name__ == "__main__":
    main()
