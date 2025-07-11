import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)
from game_manager import GameManager  # Ayrı dosyada oyun mekanikleri burada

logging.basicConfig(level=logging.INFO)

TOKEN = "YOUR_BOT_TOKEN_HERE"

with open("roles.json", "r", encoding="utf-8") as f:
    ROLES = json.load(f)

game_manager = GameManager()

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
    # GIF'i ayrı mesaj olarak gönder
    await update.message.reply_animation(gif_url)
    await update.message.reply_text(start_text, reply_markup=reply_markup)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == "commands":
        commands_text = (
            "/start : Botu başlatır\n"
            "/savas : Grupta oyunu başlatır\n"
            "/baslat : Katılımcılar tamamlandıktan sonra oyunu başlatır\n"
            "/baris : Oyunu sonlandırır\n"
            "/roles : Oyundaki ülkeleri listeler\n"
        )
        await query.message.reply_text(commands_text)
    elif data == "about":
        about_text = (
            "Bu oyun bir dünya savaşı simülasyonudur. Siz devlet başkanı sıfatıyla halkınızı "
            "nasıl yönlendireceksiniz onu görmek için yapılmıştır."
        )
        await query.message.reply_text(about_text)

async def savas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if update.effective_chat.type == "private":
        await update.message.reply_text("Oyun grup sohbetinde başlatılabilir.")
        return
    started = game_manager.start_game(chat_id)
    if not started:
        await update.message.reply_text("Oyun zaten başladı.")
        return
    await update.message.reply_text(
        "Oyun başladı! Katılmak için /katil yazın.\n\n"
        "Katılım süresi 2 dakikadır."
    )

async def baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if update.effective_chat.type == "private":
        await update.message.reply_text("Oyun grup sohbetinde başlatılabilir.")
        return
    success = game_manager.begin_game(chat_id)
    if success:
        await update.message.reply_text("Oyun başladı! İyi savaşlar!")
    else:
        await update.message.reply_text("Oyun başlatılamadı. Lütfen önce oyuncuların katıldığından emin olun.")

async def katil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    if update.effective_chat.type != "private":
        await update.message.reply_text("Lütfen oyuna katılmak için özelden bu komutu kullan.")
        return
    added = game_manager.add_player(chat_id, user.id, user.first_name)
    if added:
        await update.message.reply_text(f"{user.first_name}, oyuna katıldınız!")
        # Grup sohbetine bildirim gönder
        for group_id in game_manager.active_games.keys():
            try:
                await context.bot.send_message(group_id, f"{user.first_name} oyuna katıldı!")
            except Exception:
                pass
    else:
        await update.message.reply_text("Zaten oyundasınız veya oyun başlamış olabilir.")

async def baris(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in game_manager.active_games:
        del game_manager.active_games[chat_id]
        gif_url = "https://media.giphy.com/media/BkKhrTlrf9dqolt80i/giphy.gif"
        await update.message.reply_animation(gif_url, caption="Korkaklar gibi kaçtılar avratlar gibi savaştılar bu yüzden barışı seçtiler.")
    else:
        await update.message.reply_text("Oyunda aktif grup bulunamadı.")

async def roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    role_list = ""
    for key, val in ROLES.items():
        role_list += f"• {val['name']}: {val['power_desc']}\n"
    await update.message.reply_text(role_list)

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bilinmeyen komut. Lütfen /start ile başlayın.")

async def callback_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await game_manager.handle_callback(query)

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("savas", savas))
    app.add_handler(CommandHandler("baslat", baslat))
    app.add_handler(CommandHandler("katil", katil))
    app.add_handler(CommandHandler("baris", baris))
    app.add_handler(CommandHandler("roles", roles))
    app.add_handler(CallbackQueryHandler(callback_handler, pattern="^(commands|about)$"))
    app.add_handler(CallbackQueryHandler(callback_game))  # oyun ile ilgili callbackler

    # Bilinmeyen komutları karşılamak için:
    from telegram.ext import MessageHandler, filters
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    app.run_polling()

if __name__ == "__main__":
    main()
