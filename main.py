import os
import json
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler,
    ContextTypes, filters
)
from game_manager import GameManager

logging.basicConfig(level=logging.INFO)

# --- Token kontrolü ---
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("Bot token'ı ortam değişkeni olarak tanımlanmalı!")

# --- Roller dosyası ---
with open("roles.json", "r", encoding="utf-8") as f:
    ROLES = json.load(f)

game_manager = GameManager()
katilim_sureleri = {}  # chat_id: asyncio.Task


# --- /start komutu ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    user = update.effective_user

    # /start join_<chat_id>
    if args and args[0].startswith("join_"):
        try:
            chat_id = int(args[0].split("_")[1])
        except:
            await update.message.reply_text("Geçersiz bağlantı.")
            return

        added = game_manager.add_player(chat_id, user.id, user.first_name)
        if added:
            try:
                await context.bot.send_message(chat_id, f"{user.first_name} oyuna katıldı!")
            except:
                pass
            await update.message.reply_text("Katıldınız! Oyun yakında başlayacak.")
        else:
            await update.message.reply_text("Zaten katıldınız veya oyun başladı.")
        return

    # Normal start
    gif = "https://media.giphy.com/media/6qbNRDTBpzmYChvX85/giphy.gif"
    text = (
        f"Son bir Savaş istiyorum senden yeğen son bir savaş git onlara söyle olur mu, {user.first_name}.\n"
        "Eğlenceye katılmak için grubunuzdaki Katıl butonuna tıklayın!"
    )
    keyboard = [
        [InlineKeyboardButton("Komutlar", callback_data="commands")],
        [InlineKeyboardButton("Oyun Hakkında", callback_data="about")],
    ]
    await update.message.reply_animation(gif, caption=text, reply_markup=InlineKeyboardMarkup(keyboard))


# --- /savas komutu ---
async def savas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("Bu komut sadece gruplarda.")
        return

    chat_id = update.effective_chat.id
    if not game_manager.start_game(chat_id):
        await update.message.reply_text("Zaten aktif bir oyun var.")
        return

    katil_buton = InlineKeyboardMarkup([
        [InlineKeyboardButton("Katıl", url=f"https://t.me/{context.bot.username}?start=join_{chat_id}")]
    ])
    await update.message.reply_text(
        "Oyun başlıyor!\n⏳ Katılım süresi: 2 dakika\nEn az 5, en fazla 20 kişi.",
        reply_markup=katil_buton
    )

    async def zamanlayici():
        for kalan in [90, 60, 30]:
            await asyncio.sleep(30)
            await context.bot.send_message(chat_id, f"⏳ Oyunun başlamasına {kalan} saniye kaldı!")
        await baslat_oyun(chat_id, context)

    katilim_sureleri[chat_id] = asyncio.create_task(zamanlayici())


# --- Oyun Başlatıcı ---
async def baslat_oyun(chat_id, context):
    players = game_manager.active_games.get(chat_id).players
    if not players or len(players) < 5:
        await context.bot.send_message(chat_id, "Yeterli oyuncu yok. Oyun iptal edildi.")
        del game_manager.active_games[chat_id]
        return

    game_manager.assign_roles(chat_id)

    for user_id, pdata in players.items():
        role = pdata["role"]
        try:
            msg = f"🎖 Rolünüz: {role['name']}\n🧠 Gücünüz: {role['power_name']}\n🔮 Açıklama: {role['power_desc']}"
            gif = role.get("gif", "")
            await context.bot.send_message(chat_id=user_id, text=msg)
            if gif:
                await context.bot.send_animation(chat_id=user_id, animation=gif)
        except Exception as e:
            print(f"PM gönderilemedi: {e}")

    await context.bot.send_message(chat_id, "🎮 Roller dağıtıldı! Oyun başladı!")


# --- /basla komutu ---
async def basla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in katilim_sureleri:
        katilim_sureleri[chat_id].cancel()
        del katilim_sureleri[chat_id]
    await baslat_oyun(chat_id, context)


# --- /baris komutu ---
async def baris(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in game_manager.active_games:
        del game_manager.active_games[chat_id]
        gif = "https://media.giphy.com/media/BkKhrTlrf9dqolt80i/giphy.gif"
        await update.message.reply_animation(
            gif,
            caption="Avrat gibi savaştınız, avrat gibi oynadınız. Bu gün barış diyenler, yarın savaş diyecek. Oyun bitti, dağılın."
        )
    else:
        await update.message.reply_text("Aktif bir oyun yok.")


# --- /katil komutu ---
async def katil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Oyuna katılmak için gruptaki 'Katıl' butonunu kullanın.")


# --- /roles komutu ---
async def roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = ""
    for role in ROLES.values():
        msg += f"• {role['name']}: {role['power_desc']}\n"
    await update.message.reply_text(msg)


# --- Butonlar ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    await update.callback_query.answer()

    if data == "commands":
        await update.callback_query.edit_message_text(
            "/start - Botu başlat\n"
            "/savas - Oyunu başlatır\n"
            "/katil - Katılım için bilgi\n"
            "/baris - Oyunu bitirir\n"
            "/roles - Ülke rolleri\n"
            "/basla - Oyunu erkenden başlat"
        )
    elif data == "about":
        await update.callback_query.edit_message_text(
            "Oyunumuz, Zeyd A.I. tarafından geliştirilmiş bir savaş simülasyon botudur. "
            "Strateji, eğlence ve diplomasi bu oyunda birleşti!"
        )


# --- Callback Vote/Power ---
async def callback_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await game_manager.handle_callback(update, context)


# --- Bilinmeyen komutlar ---
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bilinmeyen komut. Lütfen /start yazın.")


# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("savas", savas))
    app.add_handler(CommandHandler("basla", basla))
    app.add_handler(CommandHandler("baris", baris))
    app.add_handler(CommandHandler("katil", katil))
    app.add_handler(CommandHandler("roles", roles))

    app.add_handler(CallbackQueryHandler(callback_handler, pattern="^(commands|about)$"))
    app.add_handler(CallbackQueryHandler(callback_game, pattern="^(vote_|power_)"))

    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    app.run_polling()


if __name__ == "__main__":
    main()
