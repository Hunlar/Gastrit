import asyncio
import json
import logging
import os
import random
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from game_manager import GameManager  # Daha önce sağladığın GameManager.py

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("Bot token'ı TOKEN ortam değişkeninde ayarlanmalı!")

with open("roles.json", "r", encoding="utf-8") as f:
    ROLES = json.load(f)

game_manager = GameManager()

# Global katılım zamanlayıcı task tutucu {chat_id: asyncio.Task}
join_tasks = {}

# Global katılım süresi saniye olarak
JOIN_DURATION = 120

# Kalan süreyi gruba bildirme aralığı
STATUS_INTERVAL = 30


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    user = update.effective_user

    # Eğer /start join_ ile geldiyse oyuncuyu oyuna ekle
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
            except Exception as e:
                print(f"Katılım bildirimi gönderilemedi: {e}")
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
            "/savas : Grupta oyunu başlatır\n"
            "/basla : Erken oyun başlatma (min 5 kişi)\n"
            "/baris : Oyunu sonlandırır\n"
            "/roles : Oyundaki ülkeleri listeler\n"
        )
        await query.edit_message_text(commands_text)
    elif data == "about":
        about_text = (
            "Oyunumuz Zeyd AI ile düzenlenmiş bir Savaş Oyun Simülasyon botudur."
        )
        await query.edit_message_text(about_text)


async def savas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("Bu komut sadece gruplarda çalışır.")
        return

    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title or "Bilinmeyen Grup"

    if chat_id in game_manager.active_games:
        await update.message.reply_text("Zaten aktif bir oyun var.")
        return

    game_manager.start_game(chat_id)

    # Katıl butonu gruba gönderiliyor
    katil_button = InlineKeyboardMarkup([
        [InlineKeyboardButton("Katıl", url=f"https://t.me/{context.bot.username}?start=join_{chat_id}")]
    ])

    await update.message.reply_text(
        f"Oyuna katılmak isteyenler aşağıdaki butona tıklayıp bota başlasın:\n\n"
        f"📍 Grup: {chat_title}\n⏱ Katılım süresi: {JOIN_DURATION // 60} dakika",
        reply_markup=katil_button
    )

    # Katılım süresi boyunca kalan süreyi 30 saniyede bir gruba bildir
    if chat_id in join_tasks:
        join_tasks[chat_id].cancel()
    join_tasks[chat_id] = asyncio.create_task(join_timer(chat_id, context))


async def join_timer(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    try:
        remaining = JOIN_DURATION
        while remaining > 0:
            await asyncio.sleep(STATUS_INTERVAL)
            remaining -= STATUS_INTERVAL
            await context.bot.send_message(chat_id, f"Oyuna katılmak için {remaining} saniye kaldı!")
        # Süre dolunca oyun başlat
        await auto_start_game(chat_id, context)
    except asyncio.CancelledError:
        # Task iptal edildiğinde sessizce çık
        pass


async def auto_start_game(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    game = game_manager.active_games.get(chat_id)
    if not game:
        await context.bot.send_message(chat_id, "Oyunu başlatmak için aktif bir oyun bulunamadı.")
        return

    player_count = len(game.players)
    if player_count < 5:
        await context.bot.send_message(chat_id, f"Oyuna en az 5 kişi katılmalı! Şu an {player_count} kişi var. Oyun başlamadı.")
        # Oyunu iptal et, katılım devam edebilir
        del game_manager.active_games[chat_id]
        if chat_id in join_tasks:
            join_tasks[chat_id].cancel()
            del join_tasks[chat_id]
        return

    if player_count > 20:
        await context.bot.send_message(chat_id, f"Oyuncu sayısı en fazla 20 olabilir, şu an {player_count} kişi var. Fazla oyuncular elenecek.")

    # Rolleri dağıt
    success = game_manager.assign_roles(chat_id)
    if not success:
        await context.bot.send_message(chat_id, "Roller dağıtılamadı. Lütfen tekrar deneyin.")
        return

    await context.bot.send_message(chat_id, f"Oyun başladı! Toplam oyuncu sayısı: {player_count}. Roller dağıtıldı. Güçlerinizi kullanabilirsiniz!")

    # Katılım süreci bitti, task iptal ve temizle
    if chat_id in join_tasks:
        join_tasks[chat_id].cancel()
        del join_tasks[chat_id]


async def basla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    game = game_manager.active_games.get(chat_id)
    if not game:
        await update.message.reply_text("Aktif bir oyun yok. /savas ile yeni oyun başlatın.")
        return

    player_count = len(game.players)
    if player_count < 5:
        await update.message.reply_text(f"Oyuna en az 5 kişi katılmalı! Şu an {player_count} kişi var.")
        return
    if player_count > 20:
        await update.message.reply_text(f"Oyuncu sayısı en fazla 20 olabilir, şu an {player_count} kişi var.")
        return

    if game.started:
        await update.message.reply_text("Oyun zaten başladı!")
        return

    # Rolleri dağıt ve başlat
    success = game_manager.assign_roles(chat_id)
    if not success:
        await update.message.reply_text("Roller dağıtılamadı. Lütfen tekrar deneyin.")
        return

    await context.bot.send_message(chat_id, f"Erken başlatıldı! Toplam oyuncu sayısı: {player_count}. Roller dağıtıldı. Oyuna başlayabilirsiniz!")

    # Eğer join timer varsa iptal et
    if chat_id in join_tasks:
        join_tasks[chat_id].cancel()
        del join_tasks[chat_id]


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


async def katil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Bu komut iptal, oyuncular /start join_ linki ile katılacaklar
    await update.message.reply_text("Oyuna katılmak için gruptaki Katıl butonuna tıklayın.")


async def callback_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await game_manager.handle_callback(update, context)


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("savas", savas))
    app.add_handler(CommandHandler("basla", basla))
    app.add_handler(CommandHandler("katil", katil))  # sadece uyarı için
    app.add_handler(CommandHandler("baris", baris))
    app.add_handler(CommandHandler("roles", roles))

    app.add_handler(CallbackQueryHandler(callback_handler, pattern="^(commands|about)$"))
    app.add_handler(CallbackQueryHandler(callback_game, pattern="^(vote_|power_)"))

    # Bilinmeyen komutları karşılamak için MessageHandler
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    app.run_polling()


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bilinmeyen komut. Lütfen /start ile başlayın.")


if __name__ == "__main__":
    main()
