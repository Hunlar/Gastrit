import asyncio
import os
import json
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN ortam değişkeni tanımlı değil!")

# Roller
with open("roles.json", encoding="utf-8") as f:
    ROLES = json.load(f)

class GameManager:
    def __init__(self):
        self.active_games = {}  # chat_id: GameData

    class GameData:
        def __init__(self):
            self.players = {}  # user_id: {"username", "role", "alive", "power_used"}
            self.started = False
            self.joining = False
            self.round = 0
            self.votes = {}
            self.vote_task = None
            self.join_task = None
            self.power_phase = False

    def start_game(self, chat_id):
        if chat_id in self.active_games:
            return False
        self.active_games[chat_id] = self.GameData()
        return True

    def add_player(self, chat_id, user_id, username):
        game = self.active_games.get(chat_id)
        if not game or game.started or not game.joining:
            return False
        if user_id not in game.players:
            game.players[user_id] = {
                "username": username,
                "role": None,
                "alive": True,
                "power_used": False,
            }
            return True
        return False

    def can_start(self, chat_id):
        game = self.active_games.get(chat_id)
        if not game:
            return False
        count = len(game.players)
        return 5 <= count <= 20

    def assign_roles_and_notify(self, chat_id, bot):
        game = self.active_games.get(chat_id)
        if not game:
            return False

        players = list(game.players.keys())
        random.shuffle(players)
        roles_list = list(ROLES.values())

        for i, user_id in enumerate(players):
            role = roles_list[i % len(roles_list)]
            game.players[user_id]["role"] = role
            game.players[user_id]["power_used"] = False

        game.started = True
        game.joining = False
        game.round = 1
        game.power_phase = False

        for user_id in players:
            role = game.players[user_id]["role"]
            keyboard = [
                [InlineKeyboardButton("Gücümü Kullan", callback_data="use_power")]
            ]
            markup = InlineKeyboardMarkup(keyboard)
            text = (
                f"🎭 Rolünüz: {role['name']}\n"
                f"💥 Gücünüz: {role.get('power', 'Yok')}"
            )
            try:
                bot.send_message(user_id, text=text, reply_markup=markup)
            except Exception as e:
                print(f"Özel mesaj gönderilemedi {user_id}: {e}")

        asyncio.create_task(bot.send_message(chat_id, f"Oyun başladı! {len(players)} oyuncu katıldı. İlk tur başladı."))
        return True

    def alive_players(self, chat_id):
        game = self.active_games.get(chat_id)
        if not game:
            return []
        return [uid for uid, p in game.players.items() if p["alive"]]

    def eliminate_player(self, chat_id, user_id):
        game = self.active_games.get(chat_id)
        if not game:
            return False
        if user_id in game.players:
            game.players[user_id]["alive"] = False
            return True
        return False

    def stop_game(self, chat_id):
        if chat_id in self.active_games:
            del self.active_games[chat_id]
            from telegram.ext import CommandHandler, CallbackQueryHandler

game_manager = GameManager()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Komutlar", callback_data="commands")],
        [InlineKeyboardButton("Oyun Hakkında", callback_data="about")]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🎮 Ülke Savaşlarına Hoş Geldin!\nKatılmak için /katil yazabilirsin.",
        reply_markup=markup
    )

async def katil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    joined = game_manager.add_player(chat_id, user.id, user.first_name)

    if joined:
        await context.bot.send_message(chat_id, f"✅ {user.first_name} oyuna katıldı.")
    else:
        await update.message.reply_text("❗ Katılamadınız. Oyun başlamış olabilir veya zaten katıldınız.")

async def savas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    started = game_manager.start_game(chat_id)
    if not started:
        await update.message.reply_text("❗ Oyun zaten başlatılmış.")
        return

    game = game_manager.active_games[chat_id]
    game.joining = True
    await update.message.reply_text("🎮 Katılım başladı! Katılmak için /katil yazın. 2 dakika süreniz var...")

    async def countdown():
        for remaining in [90, 60, 30]:
            await asyncio.sleep(30)
            await context.bot.send_message(chat_id, f"⏳ Kalan süre: {remaining} saniye")
        await asyncio.sleep(30)
        await basla(update, context, from_timer=True)

    game.join_task = asyncio.create_task(countdown())

async def basla(update: Update, context: ContextTypes.DEFAULT_TYPE, from_timer=False):
    chat_id = update.effective_chat.id
    game = game_manager.active_games.get(chat_id)

    if not game:
        await update.message.reply_text("Oyun bulunamadı.")
        return

    if not game_manager.can_start(chat_id):
        await update.message.reply_text("❗ En az 5, en fazla 20 oyuncu ile başlayabilirsiniz.")
        return

    # Katılımı durdur ve rolleri ata
    success = game_manager.assign_roles_and_notify(chat_id, context.bot)
    if success:
        await context.bot.send_message(chat_id, "🎲 Roller dağıtıldı. Oyun başladı.")
        await game_manager._power_phase_timeout(chat_id, context)

async def baris(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    game_manager.stop_game(chat_id)
    await update.message.reply_text("🕊️ Oyun sonlandırıldı.\nhttps://media.giphy.com/media/3orieZZRe4UoRzZWUE/giphy.gif")

async def komutlar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""📜 Komutlar:
/start – Başlat
/katil – Katıl
/savas – Oyunu başlat
/basla – Süreyi beklemeden başlat
/baris – Oyunu bitir
/roller – Roller listesi""")

async def roller(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "🎭 Roller:\n"
    for role in ROLES:
        msg += f"- {role['name']}: {role['power']}\n"
    await update.message.reply_text(msg)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "commands":
        await query.answer()
        await query.message.edit_text("📜 Komutlar:\n/start, /katil, /savas, /basla, /baris, /roller")
    elif data == "about":
        await query.answer()
        await query.message.edit_text("🧠 Oyunumuz Zeyd AI ile düzenlenmiş bir savaş simülasyon botudur.")
    else:
        await game_manager.handle_callback(update, context)

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("katil", katil))
    app.add_handler(CommandHandler("savas", savas))
    app.add_handler(CommandHandler("basla", basla))
    app.add_handler(CommandHandler("baris", baris))
    app.add_handler(CommandHandler("komutlar", komutlar))
    app.add_handler(CommandHandler("roller", roller))
    app.add_handler(CallbackQueryHandler(callback_handler))

    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
