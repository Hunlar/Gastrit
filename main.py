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

# Örnek roller, gerçekte roles.json veya game_manager'dan yüklenmeli
ROLES = [
    {"name": "Osmanlı İmparatorluğu", "power": "2 oylamada bir ülke saf dışı bırakabilir", "gif": "https://media.giphy.com/media/gFiY5QBLqvrx2/giphy.gif"},
    {"name": "German İmparatorluğu", "power": "2 oylamada bir kaos çıkarır", "gif": "https://media.giphy.com/media/5xaOcLGvzHxDKjufnLW/giphy.gif"},
    # ... diğer roller
]

# Oyun durumu için global dict (chat_id -> game_data)
games = {}

# Başlangıç mesajındaki gif ve metin
START_GIF = "https://media.giphy.com/media/6qbNRDTBpzmYChvX85/giphy.gif"
START_TEXT = (
    "Son bir Savaş istiyorum senden yeğen son bir savaş git onlara söyle olur mu, {username} "
    "Emaneti olan Şehri Telegramı geri alacakmış de, de onlara olur mu.\n"
    "Eğlenceye katılmak İçin Botu gruba ekle ve dostlarınla savaşı hisset"
)

# Komut ve oyun hakkında butonlar
MAIN_BUTTONS = [
    [InlineKeyboardButton("Komutlar", callback_data="commands")],
    [InlineKeyboardButton("Oyun Hakkında", callback_data="about")],
    [InlineKeyboardButton("Destek Grubu", url="https://t.me/Kizilsancaktr")],
    [InlineKeyboardButton("Zeyd Bin Sabr", url="https://t.me/ZeydBinhalit")],
]

# /start komutu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.effective_chat.type
    user = update.effective_user

    if chat_type == "private":
        await update.message.reply_text(
            "Merhaba! Bu bot bir dünya savaşı simülasyon oyunudur.\n"
            "Oyuna katılmak için grupta /savas komutunu kullanın."
        )
        return

    chat_id = update.effective_chat.id
    username = user.first_name or user.username or "Oyuncu"

    # Başlangıç oyun datası oluştur (katılım başlatılmadı)
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

# /savas komutu — oyuna katılımı başlatır
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

    # Katıl butonu, kullanıcıyı PM'ye yönlendirir (start bot private)
    join_button = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Katıl", url=f"tg://user?id={update.effective_user.id}")]]
    )

    gif_join = "https://media4.giphy.com/media/v1.Y2lkPTZjMDliOTUycmhlM2FmNm55cDVzNmdwOW4xNGRocmNpamRhaXI3cmF3M2RuOXFqYSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/14p5u4rpoC9Rm0/giphy.gif"
    await context.bot.send_animation(chat_id=chat_id, animation=gif_join)
    await context.bot.send_message(
        chat_id=chat_id,
        text="Oyuna katılmak için aşağıdaki 'Katıl' butonuna tıklayın. Katılım 2 dakika sürecek.",
        reply_markup=join_button,
    )

    # Katılım süresi sonrası oyun otomatik başlatılabilir (timeout kodu eklenmeli)
    # Buraya async delay ve basla() çağrısı eklenebilir.

# /katil komutu — oyuncular özel mesaj ile katılır (bu botun PM’de start ile başlaması gerekir)
async def katil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    # Özel mesajda kullanıcı oyuna katılabilir, ancak hangi chat'ta bilmiyoruz, ek mantık gerekir
    await update.message.reply_text(
        "Oyuna katılmak için grupta /savas komutu ile katılım başlatılmalıdır."
    )

# /basla komutu — oyuncu sayısını kontrol eder ve oyunu başlatır
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

    # Oyun başladı mesajı ve gif
    savas_gif = "https://media4.giphy.com/media/v1.Y2lkPTZjMDliOTUycmhlM2FmNm55cDVzNmdwOW4xNGRocmNpamRhaXI3cmF3M2RuOXFqYSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/14p5u4rpoC9Rm0/giphy.gif"
    await context.bot.send_animation(chat_id=chat_id, animation=savas_gif)
    await context.bot.send_message(chat_id=chat_id, text=f"Oyun başladı! Toplam {player_count} oyuncu var.")

    # Her oyuncuya rolünü ve gücünü özel mesaj olarak gönder
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
            # Kullanıcı botu engellemiş olabilir, atlayalım
            pass

# /baris komutu — oyunu sonlandırır
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

# Komutlar butonu callback
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

# Botu çalıştırmak için ana fonksiyon
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
