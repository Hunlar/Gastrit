import os
import random
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaAnimation,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN environment variable is required")

ROLES = [
    {"name": "Osmanlı İmparatorluğu", "power": "2 oylamada bir ülke saf dışı bırakabilir", "gif": "https://media.giphy.com/media/gFiY5QBLqvrx2/giphy.gif"},
    {"name": "German İmparatorluğu", "power": "2 oylamada bir kaos çıkarır", "gif": "https://media.giphy.com/media/5xaOcLGvzHxDKjufnLW/giphy.gif"},
    # ... diğer roller
]

games = {}

START_GIF = "https://media.giphy.com/media/6qbNRDTBpzmYChvX85/giphy.gif"
START_TEXT = (
    "Son bir Savaş istiyorum senden yeğen son bir savaş git onlara söyle olur mu, {username} "
    "Emaneti olan Şehri Telegramı geri alacakmış de, de onlara olur mu.\n"
    "Eğlenceye katılmak İçin Botu gruba ekle ve dostlarınla savaşı hisset"
)

MAIN_BUTTONS = [
    [InlineKeyboardButton("Komutlar", callback_data="commands")],
    [InlineKeyboardButton("Oyun Hakkında", callback_data="about")],
    [InlineKeyboardButton("Destek Grubu", url="https://t.me/Kizilsancaktr")],
    [InlineKeyboardButton("Zeyd Bin Sabr", url="https://t.me/ZeydBinhalit")],
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.effective_chat.type
    user = update.effective_user
    args = context.args

    if chat_type == "private":
        if args and args[0].startswith("join_"):
            chat_id_str = args[0][5:]
            try:
                chat_id = int(chat_id_str)
            except:
                await update.message.reply_text("Geçersiz katılım parametresi.")
                return

            if chat_id in games and games[chat_id].get("joining"):
                if user.id in games[chat_id]["players"]:
                    await update.message.reply_text("Zaten oyuna katıldınız.")
                else:
                    games[chat_id]["players"][user.id] = {"name": user.full_name, "role": None}
                    await update.message.reply_text(f"Başarıyla oyuna katıldınız! {user.full_name}")
                    try:
                        await context.bot.send_message(chat_id=chat_id, text=f"🎉 {user.full_name} oyuna katıldı!")
                    except:
                        pass
            else:
                await update.message.reply_text("Bu sohbet için katılım aktif değil veya oyun başlamış.")
            return

        await update.message.reply_text(
            "Merhaba! Bu bot bir dünya savaşı simülasyon oyunudur.\n"
            "Oyuna katılmak için grupta /savas komutunu kullanın."
        )
        return

    chat_id = update.effective_chat.id
    username = user.first_name or user.username or "Oyuncu"

    if chat_id not in games:
        games[chat_id] = {
            "players": {},
            "started": False,
            "joining": False,
        }

    text = START_TEXT.format(username=username)
    keyboard = InlineKeyboardMarkup(MAIN_BUTTONS)

    await context.bot.send_animation(chat_id=chat_id, animation=START_GIF)
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)


async def savas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in games:
        games[chat_id] = {"players": {}, "started": False, "joining": True}
    else:
        if games[chat_id]["started"]:
            await update.message.reply_text("Oyun zaten başladı.")
            return
        games[chat_id]["joining"] = True
        games[chat_id]["players"] = {}

    join_button = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Katıl", url=f"https://t.me/Zeydoyunbot?start=join_{chat_id}")]]
    )

    gif_join = "https://media4.giphy.com/media/v1.Y2lkPTZjMDliOTUycmhlM2FmNm55cDVzNmdwOW4xNGRocmNpamRhaXI3cmF3M2RuOXFqYSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/14p5u4rpoC9Rm0/giphy.gif"
    await context.bot.send_animation(chat_id=chat_id, animation=gif_join)
    await context.bot.send_message(
        chat_id=chat_id,
        text="Oyuna katılmak için aşağıdaki 'Katıl' butonuna tıklayın. Katılım 2 dakika sürecek.",
        reply_markup=join_button,
    )


async def katil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        "Oyuna katılmak için grupta /savas komutu ile katılım başlatılmalıdır."
    )


async def basla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in games or not games[chat_id].get("joining"):
        await update.message.reply_text("Henüz katılım başlamadı.")
        return
    game = games[chat_id]
    if game.get("started"):
        await update.message.reply_text("Oyun zaten başladı.")
        return

    player_count = len(game["players"])
    if player_count < 5:
        await update.message.reply_text("Oyun başlatmak için en az 5 oyuncu gerekli.")
        return
    if player_count > 20:
        await update.message.reply_text("En fazla 20 oyuncu ile oynanabilir.")
        return

    players = list(game["players"].keys())
    random.shuffle(players)
    role_count = len(ROLES)

    for i, user_id in enumerate(players):
        game["players"][user_id]["role"] = ROLES[i % role_count]

    game["started"] = True
    game["joining"] = False

    savas_gif = "https://media4.giphy.com/media/v1.Y2lkPTZjMDliOTUycmhlM2FmNm55cDVzNmdwOW4xNGRocmNpamRhaXI3cmF3M2RuOXFqYSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/14p5u4rpoC9Rm0/giphy.gif"
    await context.bot.send_animation(chat_id=chat_id, animation=savas_gif)
    await context.bot.send_message(chat_id=chat_id, text=f"Oyun başladı! Toplam {player_count} oyuncu var.")

    for user_id in players:
        role = game["players"][user_id]["role"]
        text = (
            f"🎭 Rolünüz: {role['name']}\n"
            f"💥 Gücünüz: {role.get('power', 'Yok')}\n\n"
            "Gücünüzü kullanmak için PM üzerinden butonları kullanabilirsiniz."
        )
        try:
            await context.bot.send_message(user_id, text=text)
        except:
            pass


async def baris(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in games or not games[chat_id].get("started"):
        await update.message.reply_text("Oyun henüz başlamadı.")
        return

    games.pop(chat_id)

    text = "Korkaklar gibi kaçtılar avratlar gibi savaştılar bu yüzden barışı seçtiler"
    gif = "https://media1.giphy.com/media/v1.Y2lkPTZjMDliOTUya2NuNXY3YXk5dnhjZW9kcHF3MjE4eDl4emI5MGZqNzlqdWV0YjlndSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/BkKhrTlrf9dqolt80i/giphy.gif"

    await context.bot.send_animation(chat_id=chat_id, animation=gif)
    await context.bot.send_message(chat_id=chat_id, text=text)


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "commands":
        text = (
            "/start - Botu başlatır\n"
            "/savas - Grupta oyuna katılım başlatır\n"
            "/basla - Oyunu başlatır\n"
            "/baris - Oyunu sonlandırır\n"
            "/destek - Destek grubunu gösterir"
        )
        await query.edit_message_text(text=text)

    elif query.data == "about":
        text = "Bu oyun bir dünya savaşı simülasyonudur..."
        await query.edit_message_text(text=text)


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("savas", savas))
    app.add_handler(CommandHandler("basla", basla))
    app.add_handler(CommandHandler("baris", baris))
    app.add_handler(CallbackQueryHandler(callback_handler))

    print("Bot çalışıyor...")
    app.run_polling()


if __name__ == "__main__":
    main()
