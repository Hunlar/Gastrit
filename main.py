import asyncio
import json
import random
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes,
)

# roles.json dosyasını yükle (listede olduğu varsayılıyor)
with open("roles.json", encoding="utf-8") as f:
    ROLES = json.load(f)  # Liste formatında

class GameManager:
    def __init__(self):
        self.active_games = {}  # chat_id: GameData

    class GameData:
        def __init__(self):
            self.players = {}  # user_id: {"username": str, "role": dict, "alive": bool, "power_used": bool}
            self.started = False
            self.joining = False
            self.round = 0
            self.votes = {}  # user_id: target_user_id
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
            game.players[user_id] = {"username": username, "role": None, "alive": True, "power_used": False}
            return True
        return False

    def can_start(self, chat_id):
        game = self.active_games.get(chat_id)
        if not game:
            return False
        count = len(game.players)
        return 5 <= count <= 20

    async def assign_roles_and_notify(self, chat_id, bot):
        game = self.active_games.get(chat_id)
        if not game:
            return False

        players = list(game.players.keys())
        random.shuffle(players)
        roles_list = ROLES

        # Rolleri sırayla dağıt
        for i, user_id in enumerate(players):
            role = roles_list[i % len(roles_list)]
            game.players[user_id]["role"] = role
            game.players[user_id]["power_used"] = False

        game.started = True
        game.joining = False
        game.round = 1
        game.power_phase = False

        # Rolleri özel mesajla gönder (async ve hata yakalamalı)
        for user_id in players:
            role = game.players[user_id]["role"]
            keyboard = [
                [InlineKeyboardButton("Gücümü Kullan", callback_data="use_power")]
            ]
            markup = InlineKeyboardMarkup(keyboard)
            text = (
                f"🎭 Rolünüz: {role['name']}\n"
                f"💥 Gücünüz: {role.get('power', 'Yok')}\n"
                f"📜 Açıklama: {role.get('power', '')}"
            )
            try:
                await bot.send_message(user_id, text=text, reply_markup=markup)
            except Exception as e:
                print(f"Özel mesaj gönderilemedi {user_id}: {e}")

        # Başlangıç mesajı grup chatine gönder
        await bot.send_message(chat_id, f"Oyun başladı! {len(players)} oyuncu katıldı. İlk tur başladı.")

        return True

    # Burada diğer metodlar olacak (sonraki parçada)

game_manager = GameManager()
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    keyboard = [
        [InlineKeyboardButton("Katıl", callback_data=f"join_{chat_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Oyuna katılmak için butona tıklayın!",
        reply_markup=reply_markup
    )

async def join_game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    data = query.data

    if not data.startswith("join_"):
        await query.answer()
        return

    chat_id = int(data.split("_")[1])

    # Oyunu başlatmamışsa başlat
    if chat_id not in game_manager.active_games:
        game_manager.start_game(chat_id)

    added = game_manager.add_player(chat_id, user.id, user.full_name)
    if added:
        await query.answer("Oyuna katıldınız!")
        # Gruba katılan kullanıcıyı bildir
        try:
            await context.bot.send_message(chat_id, f"{user.full_name} oyuna katıldı.")
        except Exception as e:
            print(f"Gruba katılım mesajı gönderilemedi: {e}")
    else:
        await query.answer("Zaten oyuna katıldınız veya oyun başladı.")

async def basla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if not game_manager.can_start(chat_id):
        await update.message.reply_text("Oyunu başlatmak için 5-20 arası oyuncu olmalı.")
        return

    success = await game_manager.assign_roles_and_notify(chat_id, context.bot)
    if success:
        await update.message.reply_text("Oyun başarıyla başladı!")
    else:
        await update.message.reply_text("Oyun başlatılamadı.")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    # Burada oyunun callback işlemleri olacak (güç kullanımı, oy kullanma vs.)
    # Daha sonra eklenecek, şimdilik cevapla
    await query.answer("Bu özellik henüz aktif değil.")

def main():
    token = os.getenv("TOKEN")
    if not token:
        raise RuntimeError("TOKEN environment variable is missing")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(join_game_callback, pattern=r"^join_\d+$"))
    app.add_handler(CommandHandler("basla", basla))
    app.add_handler(CallbackQueryHandler(callback_handler))

    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
