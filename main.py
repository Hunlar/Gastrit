import os
import json
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)
from game_manager import GameManager

# Logging
logging.basicConfig(level=logging.INFO)

# Ortam değişkenlerini yükle
load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("Bot token'ı ortam değişkeni olarak ayarlanmamış! Lütfen TOKEN olarak tanımlayın.")

# Roller
with open("roles.json", "r", encoding="utf-8") as f:
    ROLES = json.load(f)

game_manager = GameManager()

# /start komutu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gif_url = "https://media.giphy.com/media/6qbNRDTBpzmYChvX85/giphy.gif"
    user_name = update.effective_user.first_name
    chat_id = update.effective_chat.id

    text = (
        f"Son bir savaş istiyorum senden yeğen, son bir savaş...\n"
        f"Git onlara söyle olur mu, {user_name}!\n"
        "Emaneti olan şehri, Telegram'ı geri alacakmış de...\n\n"
        "Oyuna katılmak için aşağıdaki 'Katıl' butonuna tıkla!"
    )

    keyboard = [
        [InlineKeyboardButton("Katıl", callback_data=f"katil_{chat_id}")],
        [InlineKeyboardButton("Komutlar", callback_data="commands")],
        [InlineKeyboardButton("Oyun Hakkında", callback_data="about")],
        [InlineKeyboardButton("Destek Grubu", url="https://t.me/Kizilsancaktr")],
        [InlineKeyboardButton("Zeyd Bin Sabr", url="https://t.me/ZeydBinhalit")]
    ]
    await update.message.reply_animation(gif_url, caption=text, reply_markup=InlineKeyboardMarkup(keyboard))

# Callback butonları
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    if data.startswith("katil_"):
        chat_id = int(data.split("_")[1])
        added = game_manager.add_player(chat_id, user.id, user.first_name)
        if added:
            await query.edit_message_text(f"{user.first_name}, {chat_id} numaralı gruptaki oyuna katıldınız!")
        else:
            await query.edit_message_text("Zaten katıldınız veya oyun çoktan başladı.")

    elif data == "commands":
        text = (
            "/start – Botu başlatır\n"
            "/savas – Grupta oyunu başlatır (katılım süresi başlar)\n"
            "/baris – Oyunu sonlandırır\n"
            "/baslat – Katılım sonrası oyunu başlatır\n"
            "/roles – Oyundaki ülkeleri listeler"
        )
        await query.edit_message_text(text)

    elif data == "about":
        text = (
            "Bu oyun, mizahi bir savaş simülasyonudur.\n"
            "Her oyuncuya bir ülke atanır ve özel güçleriyle hayatta kalmaya çalışır!"
        )
        await query.edit_message_text(text)

    else:
        await game_manager.handle_callback(update, context)

# /savas – grupta başlatılır
async def savas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "group" and update.effective_chat.type != "supergroup":
        await update.message.reply_text("Bu komut sadece gruplarda çalışır.")
        return
    chat_id = update.effective_chat.id
    if game_manager.start_game(chat_id):
        await update.message.reply_text(
            "Oyun başladı! Katılmak isteyenler bota özelden /start yazsın ve 'Katıl' butonuna bassın.\n"
            "Katılım süresi: 2 dakika!"
        )
    else:
        await update.message.reply_text("Oyun zaten başlatılmış.")

# /baris – oyunu bitirir
async def baris(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in game_manager.active_games:
        del game_manager.active_games[chat_id]
        gif_url = "https://media.giphy.com/media/BkKhrTlrf9dqolt80i/giphy.gif"
        await update.message.reply_animation(
            gif_url,
            caption=(
                "Avrat gibi savaştınız, avrat gibi oynadınız. Barış sağlandı.\n\n"
                "Ey kalbi kırık bu grubun evladı...\n"
                "Bugün barış diyerek oyunu bitirenler, yarın savaş diyecekler.\n\n"
                "🎭 Oyun bitti, dağılın."
            )
        )
    else:
        await update.message.reply_text("Aktif bir oyun yok.")

# /roles – rol listesini gösterir
async def roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "Ülkeler ve özel güçleri:\n\n"
    for role in ROLES.values():
        msg += f"🌍 {role['name']}: {role['power_desc']}\n"
    await update.message.reply_text(msg)

# /baslat – oyunu başlatır
async def baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not game_manager.assign_roles(chat_id):
        await update.message.reply_text("Oyuncular yeterli değil veya oyun başlamadı.")
        return
    for user_id in game_manager.active_games[chat_id].players:
        role = game_manager.get_player_role(chat_id, user_id)
        if role:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"Rolünüz: {role['name']}\nGücünüz: {role['power_name']}\n{role['power_desc']}"
                )
            except Exception as e:
                print(f"Mesaj gönderilemedi: {e}")
    await update.message.reply_text("🎲 Roller dağıtıldı, oyun başlıyor!")

# Bilinmeyen komutlar
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bilinmeyen komut. /start ile başlayabilirsiniz.")

# Ana fonksiyon
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("savas", savas))
    app.add_handler(CommandHandler("baris", baris))
    app.add_handler(CommandHandler("baslat", baslat))
    app.add_handler(CommandHandler("roles", roles))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
