import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from game_manager import GameManager  # Ayrı dosyada oyun mekanikleri burada

logging.basicConfig(level=logging.INFO)

# Token environment variable'dan veya .env dosyasından da alınabilir
TOKEN = "YOUR_BOT_TOKEN_HERE"

# Roller dosyasını yükle
with open("roles.json", "r", encoding="utf-8") as f:
    ROLES = json.load(f)

game_manager = GameManager()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Grup sohbetindeyse özelden katılım için mesaj at
    if update.effective_chat.type != "private":
        keyboard = [
            [
                InlineKeyboardButton(
                    "Oyuna Katılmak İçin Özelden Başlat", url=f"t.me/{context.bot.username}?start=join"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Oyuna katılmak için lütfen bana özelden /start komutunu kullanın.",
            reply_markup=reply_markup,
        )
        return

    # Private chat için start mesajı ve butonlar
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
        [InlineKeyboardButton("Zeyd Bin Sabr", url="https://t.me/ZeydBinhalit")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_animation(gif_url, caption=start_text, reply_markup=reply_markup)


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "commands":
        commands_text = (
            "/start : Botu başlatır\n"
            "/savas : Grupta oyunu başlatır\n"
            "/katil : Oyuna katılır\n"
            "/baris : Oyunu sonlandırır\n"
            "/roles : Oyundaki ülkeleri listeler\n"
        )
        await query.edit_message_text(commands_text)
    elif data == "about":
        about_text = (
            "Bu oyun bir dünya savaşı simülasyonudur. Siz devlet başkanı sıfatıyla halkınızı "
            "nasıl yönlendireceksiniz onu görmek için yapılmıştır."
        )
        await query.edit_message_text(about_text)


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
        "Oyun başladı! Katılmak için bana özelden /start komutunu kullanarak katılın.\n\n"
        "Katılım süresi 2 dakikadır."
    )


async def katil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Katılım komutu özelden kullanılacak
    if update.effective_chat.type != "private":
        await update.message.reply_text("Lütfen oyuna katılmak için bana özelden /start yazın.")
        return

    user = update.effective_user
    # Her oyuncunun hangi gruba katıldığı info'yu game_manager ile tutuyoruz
    chat_id = None
    if context.args and context.args[0].startswith("join"):
        # Eğer start parametre ile geldiyse grup ID'si burada tutulabilir (düzenlenmeli)
        # Örnek: t.me/BotUsername?start=join12345678
        try:
            chat_id = int(context.args[0][4:])  # "join12345678" -> 12345678
        except Exception:
            chat_id = None

    # Eğer chat_id alınamazsa en azından bir default grup ID veya hata mesajı verilebilir.
    # Burada basitçe en azından active game varsa onun ID'sini alabiliriz
    if chat_id is None:
        # Burada 1 aktif oyun varsa ona katılıyoruz (test amaçlı)
        if game_manager.active_games:
            chat_id = list(game_manager.active_games.keys())[0]
        else:
            await update.message.reply_text(
                "Henüz aktif bir oyun bulunmamaktadır. Lütfen önce grup sohbetinde /savas komutunu kullanın."
            )
            return

    added = game_manager.add_player(chat_id, user.id, user.first_name)
    if added:
        await update.message.reply_text(f"{user.first_name}, {chat_id} oyununa katıldınız!")
        # Grup sohbetine oyuncu katıldı mesajı at
        try:
            await context.bot.send_message(chat_id, f"{user.first_name} oyuna katıldı!")
        except Exception as e:
            logging.error(f"Gruba mesaj atılırken hata: {e}")
    else:
        await update.message.reply_text("Zaten oyundasınız veya oyun başlamış olabilir.")


async def baris(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in game_manager.active_games:
        del game_manager.active_games[chat_id]
        gif_url = "https://media.giphy.com/media/BkKhrTlrf9dqolt80i/giphy.gif"
        await update.message.reply_animation(
            gif_url, caption="Korkaklar gibi kaçtılar avratlar gibi savaştılar bu yüzden barışı seçtiler."
        )
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
    # /katil komutunu artık /start içinde PM yönlendirmeden kullanılmayacak, ama yine ekleyelim hata olmasın
    app.add_handler(CommandHandler("katil", katil))
    app.add_handler(CommandHandler("baris", baris))
    app.add_handler(CommandHandler("roles", roles))
    app.add_handler(CallbackQueryHandler(callback_handler, pattern="^(commands|about)$"))
    app.add_handler(CallbackQueryHandler(callback_game))  # oyun ile ilgili callbackler

    # Bilinmeyen komutlar için MessageHandler kullanıyoruz:
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    app.run_polling()


if __name__ == "__main__":
    main()
