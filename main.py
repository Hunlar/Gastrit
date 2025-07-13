import os
import random
import asyncio
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
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
    {"name": "Britanya İmparatorluğu", "power": "Bir ülkenin oy tercihlerini manipüle eder", "gif": "https://media.giphy.com/media/fxsqOYnIMEefC/giphy.gif"},
    {"name": "Pembe Dünya", "power": "Her tur meydan okur", "gif": "https://media.giphy.com/media/13gvXfEVlxQjDO/giphy.gif"},
    {"name": "Rusya Federasyonu", "power": "Bir ülkenin oy kullanmasını 1 tur engelleyebilir", "gif": "https://media.giphy.com/media/YQitE4YNQNahy/giphy.gif"},
    {"name": "ABD", "power": "1 ülkeyi 1 tur dokunulmaz yapar", "gif": "https://media.giphy.com/media/xT0xeJpnrWC4XWblEk/giphy.gif"},
    {"name": "Fransa", "power": "Oyların 2 kat sayılmasını sağlar", "gif": "https://media.giphy.com/media/l0MYDGA3Du1hBRzzy/giphy.gif"},
    {"name": "Çin", "power": "Oylama sonuçlarını tersine çevirebilir", "gif": "https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif"},
    {"name": "İran", "power": "Gizli oy kullanır", "gif": "https://media.giphy.com/media/k7VVlKoZFkHG8/giphy.gif"},
    {"name": "İsrail", "power": "2 kişiye oy verebilir", "gif": "https://media.giphy.com/media/SUenpgdA5Ttda/giphy.gif"},
    {"name": "Türkiye", "power": "Her 3 turda bir herkesi ifşa eder", "gif": "https://media.giphy.com/media/14p5u4rpoC9Rm0/giphy.gif"},
    {"name": "Kuzey Kore", "power": "1 tur görünmez olur", "gif": "https://media.giphy.com/media/R9zXH9MdGJg7e/giphy.gif"},
    {"name": "Japonya", "power": "Rastgele bir gücü kopyalar", "gif": "https://media.giphy.com/media/8FenWQk1ntSMLtB8Nz/giphy.gif"},
    {"name": "Hindistan", "power": "1 ülkenin gücünü engeller", "gif": "https://media.giphy.com/media/WUlplcMpOCEmTGBtBW/giphy.gif"},
    {"name": "Meksika", "power": "Elenen ülkeyi geri döndürebilir", "gif": "https://media.giphy.com/media/xT0BKiaM2VGJHf9Fba/giphy.gif"},
    {"name": "İtalya", "power": "Aynı hedefe 2 oy verir", "gif": "https://media.giphy.com/media/YTbZzCkRQCEJa/giphy.gif"},
    {"name": "Brezilya", "power": "Her 4 turda bir korunur", "gif": "https://media.giphy.com/media/xT0BKiaM2VGJHf9Fba/giphy.gif"},
    {"name": "Ukrayna", "power": "Kimin hangi ülke olduğunu açığa çıkarabilir", "gif": "https://media.giphy.com/media/xT0BKiaM2VGJHf9Fba/giphy.gif"},
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

    gif_join = "https://media4.giphy.com/media/14p5u4rpoC9Rm0/giphy.gif"
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


async def send_vote_buttons(user_id, game, context):
    buttons = []
    for pid, pdata in game["players"].items():
        role_name = pdata["role"]["name"]
        buttons.append([InlineKeyboardButton(role_name, callback_data=f"vote_{pid}")])
    keyboard = InlineKeyboardMarkup(buttons)

    text = "Kime oy vermek istiyorsunuz? (Bir oyuncuya oy verin)"
    await context.bot.send_message(chat_id=user_id, text=text, reply_markup=keyboard)


async def vote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    voter_id = query.from_user.id
    data = query.data

    chat_id = None
    for c_id, game in games.items():
        if voter_id in game["players"]:
            chat_id = c_id
            break
    if chat_id is None:
        await query.answer("Oyunda değilsiniz veya oyun bulunamadı.", show_alert=True)
        return

    if not data.startswith("vote_"):
        await query.answer()
        return

    target_id_str = data[5:]
    try:
        target_id = int(target_id_str)
    except:
        await query.answer("Geçersiz seçim.", show_alert=True)
        return

    if "votes" not in games[chat_id]:
        games[chat_id]["votes"] = {}

    games[chat_id]["votes"][voter_id] = target_id

    await query.answer(f"{games[chat_id]['players'][voter_id]['role']['name']} olarak oyunuz alındı!")
    await query.edit_message_reply_markup(reply_markup=None)


def tally_votes(game):
    vote_counts = {}
    for voter, target in game.get("votes", {}).items():
        vote_counts[target] = vote_counts.get(target, 0) + 1

    if not vote_counts:
        return None

    max_votes = max(vote_counts.values())
    eliminated = [uid for uid, count in vote_counts.items() if count == max_votes]

    return eliminated


async def use_power(chat_id, context):
    game = games.get(chat_id)
    if not game or not game.get("started"):
        return

    player_count = len(game["players"])
    if player_count == 0:
        return

    powers_available = 1 if player_count < 10 else 3
    used_powers = []

    players_list = list(game["players"].items())
    random.shuffle(players_list)

    messages = {
        "Osmanlı İmparatorluğu": "Osmanlı Germen İmparatorluğunu bok gibi oyunun dışına fırlattı!",
        "German İmparatorluğu": "Germen İmparatorluğu Britanya'yı bir karışıklığa soktu!",
        "Britanya İmparatorluğu": "Britanya İmparatorluğu Rusya'nın oyununu manipüle etti!",
        "Pembe Dünya": "Pembe Dünya herkese meydan okudu!",
        "Rusya Federasyonu": "Rusya Federasyonu ABD'nin oy kullanmasını engelledi!",
        "ABD": "ABD bir ülkeyi dokunulmaz yaptı!",
        "Fransa": "Fransa oyları iki kat saydırdı!",
        "Çin": "Çin oylama sonuçlarını tersine çevirdi!",
        "İran": "İran gizli oy kullandı!",
        "İsrail": "İsrail iki kişiye oy verdi!",
        "Türkiye": "Türkiye herkesi ifşa etti!",
        "Kuzey Kore": "Kuzey Kore görünmez oldu!",
        "Japonya": "Japonya rastgele bir gücü kopyaladı!",
        "Hindistan": "Hindistan bir ülkenin gücünü engelledi!",
        "Meksika": "Meksika elenen ülkeyi geri döndürdü!",
        "İtalya": "İtalya aynı hedefe iki oy verdi!",
        "Brezilya": "Brezilya koruma sağladı!",
        "Ukrayna": "Ukrayna kimlerin hangi ülke olduğunu açığa çıkardı!",
    }

    for user_id, pdata in players_list:
        if len(used_powers) >= powers_available:
            break
        role = pdata.get("role")
        if role and role["name"] not in used_powers:
            used_powers.append(role["name"])
            message = messages.get(role["name"], f"{role['name']} özel gücünü kullandı!")
            await context.bot.send_animation(chat_id=chat_id, animation=role["gif"])
            await context.bot.send_message(chat_id=chat_id, text=message)

    # Özel güçler her 40 saniyede bir kullanılır
    await asyncio.sleep(40)
    await use_power(chat_id, context)


async def start_round(chat_id, context):
    game = games[chat_id]
    game["votes"] = {}

    for user_id in game["players"]:
        await send_vote_buttons(user_id, game, context)

    await context.bot.send_message(chat_id, "🗳 Oylama turu başladı! Oy vermek için PM'den butonları kullanın.")

    # Oylama 60 saniye sürecek
    await asyncio.sleep(60)

    await context.bot.send_message(chat_id, "🕒 Oylama süresi sona erdi. Sonuçlar hesaplanıyor...")

    eliminated = tally_votes(game)

    if eliminated:
        eliminated_names = [game["players"][uid]["role"]["name"] for uid in eliminated]
        await context.bot.send_message(chat_id, f"📢 En çok oyu alan oyuncu(lar) elendi: {', '.join(eliminated_names)}")
        for uid in eliminated:
            del game["players"][uid]
    else:
        await context.bot.send_message(chat_id, "📢 Hiç oyuncu elenemedi.")

    await asyncio.sleep(5)


async def basla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in games or not games[chat_id].get("joining"):
        await update.message.reply_text("Henüz katılım başlamadı.")
        return
    game = games[chat_id]
    if game.get("started"):
        await update.message.reply_text("Oyun zaten başladı.")
        return

    player_ids = list(game["players"].keys())
    if len(player_ids) < 5:
        await update.message.reply_text("Oyun başlatmak için en az 5 oyuncu gerekli.")
        return
    if len(player_ids) > len(ROLES):
        await update.message.reply_text("Yeterli sayıda rol yok. Maksimum oyuncu sayısı aşıldı.")
        return

    random.shuffle(player_ids)
    assigned_roles = random.sample(ROLES, len(player_ids))

    for user_id, role in zip(player_ids, assigned_roles):
        game["players"][user_id]["role"] = role

    game["started"] = True
    game["joining"] = False

    await context.bot.send_animation(chat_id=chat_id, animation="https://media4.giphy.com/media/14p5u4rpoC9Rm0/giphy.gif")
    await context.bot.send_message(chat_id=chat_id, text=f"🎮 Oyun başladı! Toplam {len(player_ids)} oyuncu var.")

    for user_id in player_ids:
        role = game["players"][user_id]["role"]
        try:
            await context.bot.send_message(
                user_id,
                f"🎭 Rolünüz: {role['name']}\n💥 Gücünüz: {role['power']}\nOylar başlayınca hazır olun."
            )
        except:
            pass

    # Aynı anda özel güç kullanımı ve oylama başlasın
    asyncio.create_task(use_power(chat_id, context))
    asyncio.create_task(start_round(chat_id, context))


async def baris(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in games or not games[chat_id].get("started"):
        await update.message.reply_text("Oyun henüz başlamadı.")
        return

    games.pop(chat_id)

    text = "Korkaklar gibi kaçtılar avratlar gibi savaştılar bu yüzden barışı seçtiler"
    gif = "https://media1.giphy.com/media/BkKhrTlrf9dqolt80i/giphy.gif"

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
    app.add_handler(CallbackQueryHandler(vote_callback, pattern=r"^vote_"))
    app.add_handler(CallbackQueryHandler(callback_handler, pattern="^(commands|about)$"))

    print("Bot çalışıyor...")
    app.run_polling()


if __name__ == "__main__":
    main()
