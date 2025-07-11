import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
)
from game_manager import GameManager  # Ayrı dosyada oyun mekanikleri burada

logging.basicConfig(level=logging.INFO)

# Token .env'den ya da config dosyasından alınmalı (güvenlik için)
import os
TOKEN = os.getenv("BOT_TOKEN")

# Roller dosyasını yükle
with open("roles.json", "r", encoding="utf-8") as f:
    ROLES = json.load(f)

game_manager = GameManager()

# /start komutu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gif_url = "https://media.giphy.com/media/6qbNRDTBpzmYChvX85/giphy.gif"
    user_name = update.effective_user.first_name
    start_text = (
        f"Son bir Savaş istiyorum senden yeğen son bir savaş git onlara söyle olur mu, {user_name} "
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
    await update.message.reply_animation(gif_url, caption=start_text, reply_markup=reply_markup)

# Buton geri dönüşleri
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "commands":
        commands_text = (
            "/start : Botu başlatır\n"
            "/savas : Oyunu başlatır\n"
            "/katil : Oyuna katılır (özelde çalışır)\n"
            "/baris : Oyunu sonlandırır\n"
            "/roles : Ülke rollerini listeler\n"
        )
        await query.edit_message_text(commands_text)
    elif data == "about":
        about_text = (
            "🌍 Bu oyun bir dünya savaşı simülasyonudur.\n"
            "Siz devlet başkanı sıfatıyla halkınızı nasıl yönlendireceksiniz onu görmek için tasarlandı."
        )
        await query.edit_message_text(about_text)

# /savas komutu
async def savas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if update.effective_chat.type == "private":
        await update.message.reply_text("❗ Oyun grup sohbetinde başlatılabilir.")
        return
    started = game_manager.start_game(chat_id)
    if not started:
        await update.message.reply_text("⚠️ Oyun zaten başlatılmış.")
        return
    await update.message.reply_text(
        "🎮 Oyun başladı! Katılmak için /katil komutunu kullan.\n⏳ Katılım süresi 2 dakikadır."
    )

# /katil komutu
async def katil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if update.effective_chat.type != "private":
        await update.message.reply_text("📥 Lütfen oyuna katılmak için özelden bu komutu kullan.")
        return
    # Katıldığı grup ID'sini kullanıcıdan al
    chat_id = game_manager.get_last_active_group()
    if not chat_id:
        await update.message.reply_text("❌ Katılabileceğiniz bir oyun şu an bulunmuyor.")
        return
    added = game_manager.add_player(chat_id, user.id, user.first_name)
    if added:
        await update.message.reply_text(f"✅ {user.first_name}, başarıyla oyuna katıldınız!")
    else:
        await update.message.reply_text("❗ Zaten katıldınız ya da oyun başladı.")

# /baris komutu
async def baris(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in game_manager.active_games:
        del game_manager.active_games[chat_id]
        gif_url = "https://media.giphy.com/media/BkKhrTlrf9dqolt80i/giphy.gif"
        await update.message.reply_animation(
            gif_url,
            caption="💔 Korkaklar gibi kaçtılar, avratlar gibi savaştılar...\nBu yüzden barışı seçtiler."
        )
    else:
        await update.message.reply_text("⚠️ Aktif bir oyun bulunamadı.")

# /roles komutu
async def roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    role_list = ""
    for role_id, role in ROLES.items():
        role_list += f"🛡 {role['name']}: {role['power_desc']}\n"
    await update.message.reply_text(role_list)

# Bilinmeyen komutlar
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bilinmeyen komut. /start ile başlayabilirsin.")

# Buton ile oyun callbackleri
async def callback_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await game_manager.handle_callback(query)

# Main fonksiyon
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("savas", savas))
    app.add_handler(CommandHandler("katil", katil))
    app.add_handler(CommandHandler("baris", baris))
    app.add_handler(CommandHandler("roles", roles))

    app.add_handler(CallbackQueryHandler(callback_handler, pattern="^(commands|about)$"))
    app.add_handler(CallbackQueryHandler(callback_game))  # Diğer oyun içi callbackler

    app.add_handler(MessageHandler(filters.COMMAND, unknown))  # bilinmeyen komutlar

    app.run_polling()

if __name__ == "__main__":
    main()
