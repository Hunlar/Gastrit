import json
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)
from game_manager import GameManager  # Ayrı dosyada oyun mekanikleri burada
import os

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("Bot token'ı ortam değişkeni olarak ayarlanmamış! Lütfen TOKEN olarak tanımlayın.")

with open("roles.json", "r", encoding="utf-8") as f:
    ROLES = json.load(f)

game_manager = GameManager()

# Süre takipleri için global dictionary: chat_id -> remaining_seconds
join_timers = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    user = update.effective_user

    if args and args[0].startswith("join_"):
        try:
            chat_id = int(args[0].split("_")[1])
        except Exception:
            await update.message.reply_text("Geçersiz başlangıç parametresi.")
            return

        added = game_manager.add_player(chat_id, user.id, user.first_name)
        if added:
            try:
                await context.bot.send_message(chat_id, f"{user.first_name} oyuna katıldı! 🎯")
                await update.message.reply_text("Katıldınız! Oyun yakında başlayacak.")
            except Exception:
                await update.message.reply_text("Katıldınız ama gruba bildirim gönderilemedi.")
        else:
            await update.message.reply_text("Zaten katıldınız veya oyun başlamış.")
        return

    gif_url = "https://media.giphy.com/media/6qbNRDTBpzmYChvX85/giphy.gif"
    user_name = user.first_name
    start_text = (
        f"Son bir Savaş istiyorum senden yeğen son bir savaş git onlara söyle olur mu, {user_name} "
        "Emaneti olan Şehri Telegramı geri alacakmış de, de onlara olur mu.\n\n"
        "Eğlenceye katılmak için oyununuzun başladığı gruptaki Katıl butonuna tıklayın!"
    )
    keyboard = [
        [InlineKeyboardButton("Komutlar", callback_data="commands")],
        [InlineKeyboardButton("Oyun Hakkında", callback_data="about")],
        [InlineKeyboardButton("Destek Grubu", url="https://t.me/Kizilsancaktr")],
        [InlineKeyboardButton("Zeyd Bin Sabr", url="https://t.me/ZeydBinhalit")]
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
            "/basla : Oyunu başlatır ve rolleri dağıtır\n"
            "/katil : Oyuna katılır (özelden)\n"
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
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("Bu komut sadece gruplarda çalışır.")
        return

    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title or "Bilinmeyen Grup"

    if not game_manager.start_game(chat_id):
        await update.message.reply_text("Zaten aktif bir oyun var.")
        return

    katil_button = InlineKeyboardMarkup([
        [InlineKeyboardButton("Katıl", url=f"https://t.me/{context.bot.username}?start=join_{chat_id}")]
    ])

    await update.message.reply_text(
        f"Oyuna katılmak isteyenler aşağıdaki butona tıklayıp bota başlasın:\n\n"
        f"📍 Grup: {chat_title}\n⏱ Katılım süresi: 2 dakika",
        reply_markup=katil_button
    )

    # 2 dakika katılım süresi ve 30 saniyede bir kalan süre bildirimi için async task başlat
    join_timers[chat_id] = 120
    asyncio.create_task(join_countdown(chat_id, context))


async def join_countdown(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    while join_timers.get(chat_id, 0) > 0:
        remaining = join_timers[chat_id]
        if remaining in [120, 90, 60, 30]:
            await context.bot.send_message(chat_id, f"Oyuna katılım için kalan süre: {remaining} saniye.")
        await asyncio.sleep(30)
        join_timers[chat_id] -= 30

    # Süre dolduğunda
    if chat_id in join_timers:
        del join_timers[chat_id]

    game = game_manager.active_games.get(chat_id)
    if not game:
        return
    player_count = len(game.players)

    if player_count < 5:
        await context.bot.send_message(chat_id, "Katılım süresi doldu fakat minimum 5 oyuncu sağlanamadı. Oyun iptal edildi.")
        del game_manager.active_games[chat_id]
        return

    if player_count > 20:
        await context.bot.send_message(chat_id, "Katılım süresi doldu fakat maksimum 20 oyuncu sınırı aşıldı. Oyun iptal edildi.")
        del game_manager.active_games[chat_id]
        return

    await context.bot.send_message(chat_id, f"Katılım süresi doldu. {player_count} oyuncu ile oyun başlatılabilir. Oyunu başlatmak için /basla komutunu kullanın.")


async def basla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    game = game_manager.active_games.get(chat_id)

    if not game:
        await update.message.reply_text("Oyun bulunamadı. Önce /savas komutu ile oyun başlatın.")
        return

    if game.started:
        await update.message.reply_text("Oyun zaten başladı.")
        return

    player_count = len(game.players)
    if player_count < 5:
        await update.message.reply_text("Oyuncu sayısı minimum 5 olmalı.")
        return

    if player_count > 20:
        await update.message.reply_text("Oyuncu sayısı maksimum 20 olmalı.")
        return

    ok = game_manager.assign_roles(chat_id)
    if not ok:
        await update.message.reply_text("Roller atanamadı, oyun başlatılamadı.")
        return

    await update.message.reply_text("Oyun başladı! Roller dağıtıldı. İyi oyunlar!")


async def katil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Oyuna katılmak için gruptaki Katıl butonuna tıklayın.")


async def baris(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in game_manager.active_games:
        del game_manager.active_games[chat_id]
        gif_url = "https://media.giphy.com/media/BkKhrTlrf9dqolt80i/giphy.gif"
        await update.message.reply_animation(
            gif_url,
            caption="avrat gibi savaştınız avrat gibi oynadınız barış sağlandı ey kalbi kırık bu grubun evladı bu gün barış diyerek oyunu bitirenler yarın savaş diyecekler. Oyun bitti dağılın"
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
    await game_manager.handle_callback(update, context)


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("savas", savas))
    app.add_handler(CommandHandler("basla", basla))
    app.add_handler(CommandHandler("katil", katil))  # Hala ekledim uyarı için
    app.add_handler(CommandHandler("baris", baris))
    app.add_handler(CommandHandler("roles", roles))

    app.add_handler(CallbackQueryHandler(callback_handler, pattern="^(commands|about)$"))
    app.add_handler(CallbackQueryHandler(callback_game, pattern="^(vote_|power_)"))

    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    app.run_polling()


if __name__ == "__main__":
    main()
