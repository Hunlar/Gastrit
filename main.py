import json
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
)
from game_manager import GameManager
import os

logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("Bot token'ı ortam değişkeni olarak ayarlanmamış! Lütfen TOKEN olarak tanımlayın.")

with open("roles.json", "r", encoding="utf-8") as f:
    ROLES = json.load(f)

game_manager = GameManager()
join_timers = {}  # chat_id: task


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

    # Normal /start mesajı
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
            "/savas : Oyunu başlatır (katılım süreci)\n"
            "/basla : Oyunu erken başlatır (en az 5 kişi)\n"
            "/baris : Oyunu sonlandırır\n"
            "/roles : Ülkeleri ve güçlerini listeler"
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

    # Geri sayım başlat
    async def countdown():
        for remaining in [90, 60, 30]:
            await asyncio.sleep(30)
            await context.bot.send_message(chat_id, f"⏳ Oyunun başlamasına {remaining} saniye kaldı!")

        players = game_manager.active_games[chat_id].players
        if 5 <= len(players) <= 20:
            game_manager.assign_roles(chat_id)
            for uid in players:
                role = game_manager.get_player_role(chat_id, uid)
                if role:
                    await context.bot.send_message(uid, f"Rolünüz: {role['name']}\nGücünüz: {role['power_desc']}")
            await context.bot.send_message(chat_id, "🎮 Oyun otomatik başladı! Roller dağıtıldı.")
        else:
            del game_manager.active_games[chat_id]
            await context.bot.send_message(chat_id, "❌ Yeterli oyuncu yok. Oyun iptal edildi.")

    join_timers[chat_id] = asyncio.create_task(countdown())


async def basla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    game = game_manager.active_games.get(chat_id)

    if not game:
        await update.message.reply_text("Aktif bir oyun yok.")
        return

    if game.started:
        await update.message.reply_text("Oyun zaten başlamış.")
        return

    players = game.players
    if not (5 <= len(players) <= 20):
        await update.message.reply_text("Oyun başlatmak için 5 ile 20 arası oyuncu olmalı.")
        return

    if chat_id in join_timers:
        join_timers[chat_id].cancel()
        del join_timers[chat_id]

    game_manager.assign_roles(chat_id)
    for uid in players:
        role = game_manager.get_player_role(chat_id, uid)
        if role:
            await context.bot.send_message(uid, f"Rolünüz: {role['name']}\nGücünüz: {role['power_desc']}")
    await update.message.reply_text("🎮 Oyun erken başlatıldı! Roller dağıtıldı.")


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
        await update.message.reply_text("Aktif oyun bulunamadı.")


async def roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    role_list = ""
    for key, val in ROLES.items():
        role_list += f"• {val['name']}: {val['power_desc']}\n"
    await update.message.reply_text(role_list)


async def katil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Oyuna katılmak için gruptaki Katıl butonuna tıklayın.")


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bilinmeyen komut. Lütfen /start ile başlayın.")


async def callback_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await game_manager.handle_callback(update, context)


def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("savas", savas))
    app.add_handler(CommandHandler("katil", katil))
    app.add_handler(CommandHandler("baris", baris))
    app.add_handler(CommandHandler("roles", roles))
    app.add_handler(CommandHandler("basla", basla))
    app.add_handler(CallbackQueryHandler(callback_handler, pattern="^(commands|about)$"))
    app.add_handler(CallbackQueryHandler(callback_game, pattern="^(vote_|power_)"))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))
    app.run_polling()


if __name__ == "__main__":
    main()
