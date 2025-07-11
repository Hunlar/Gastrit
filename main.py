import os
import json
import logging
from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)
from game_manager import GameManager

# .env varsa yükle
load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("Bot token'ı ortam değişkeni olarak ayarlanmamış! Lütfen TOKEN olarak tanımlayın.")

logging.basicConfig(level=logging.INFO)

with open("roles.json", "r", encoding="utf-8") as f:
    ROLES = json.load(f)

game_manager = GameManager()

# PM'den gelen /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gif_url = "https://media.giphy.com/media/6qbNRDTBpzmYChvX85/giphy.gif"
    user = update.effective_user
    username = user.first_name
    message = (
        f"Son bir Savaş istiyorum senden yeğen son bir savaş git onlara söyle olur mu, {username} "
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

    await update.message.reply_animation(animation=gif_url, caption=message, reply_markup=reply_markup)

# Komut butonları
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "commands":
        commands_text = (
            "/start – Botu başlatır\n"
            "/savas – Oyunu başlatır\n"
            "/katil – Katılım linki verir\n"
            "/baslat – Oyunu başlatır (Katılımlar tamamlandıysa)\n"
            "/baris – Oyunu bitirir\n"
            "/roles – Ülke rollerini listeler\n"
        )
        await query.edit_message_text(commands_text)
    elif data == "about":
        role_list = "\n".join([f"• {val['name']}: {val['power_desc']}" for val in ROLES.values()])
        await query.edit_message_text("Ülkeler ve güçleri:\n\n" + role_list)

# Grup içi /savas
async def savas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private":
        await update.message.reply_text("Bu komut sadece gruplarda çalışır.")
        return

    started = game_manager.start_game(chat.id)
    if not started:
        await update.message.reply_text("Oyun zaten başlatılmış.")
        return

    gif = "https://media4.giphy.com/media/14p5u4rpoC9Rm0/giphy.gif"
    keyboard = [[InlineKeyboardButton("Katıl", url=f"https://t.me/{context.bot.username}?start=katil_{chat.id}")]]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_animation(gif, caption="Oyuna katılmak için aşağıdaki butona tıklayın!", reply_markup=markup)

# Katılım (PM'den)
async def start_katil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message.text

    if not message.startswith("/start katil_"):
        await start(update, context)
        return

    try:
        chat_id = int(message.split("_")[1])
    except:
        await update.message.reply_text("Hatalı bağlantı.")
        return

    added = game_manager.add_player(chat_id, user.id, user.first_name)
    if added:
        await update.message.reply_text(f"{game_manager.get_chat_title(chat_id)} oyununa katıldınız.")
    else:
        await update.message.reply_text("Zaten katıldınız veya oyun başlamamış olabilir.")

# Oyunu başlat
async def baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    result = game_manager.assign_roles_and_start(chat_id)
    await update.message.reply_text(result)

# Barış
async def baris(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    gif = "https://media.giphy.com/media/BkKhrTlrf9dqolt80i/giphy.gif"
    game_manager.end_game(chat_id)
    await update.message.reply_animation(gif, caption="Korkaklar gibi kaçtılar avratlar gibi savaştılar bu yüzden barışı seçtiler.")

# Roller
async def roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "\n".join([f"• {val['name']}: {val['power_desc']}" for val in ROLES.values()])
    await update.message.reply_text(text)

# Bilinmeyen
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bilinmeyen komut. /start ile başlayın.")

# Ana fonksiyon
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_katil))
    app.add_handler(CommandHandler("savas", savas))
    app.add_handler(CommandHandler("baris", baris))
    app.add_handler(CommandHandler("baslat", baslat))
    app.add_handler(CommandHandler("roles", roles))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(CommandHandler(None, unknown))

    app.run_polling()

if __name__ == "__main__":
    main()
