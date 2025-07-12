import os
import json
import random
import asyncio
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatMemberUpdated,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# roles.json dosyasını yükle
with open("roles.json", encoding="utf-8") as f:
    ROLES = json.load(f)  # Liste formatında olduğu için values() yok!

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
        game = self.GameData()
        game.joining = True
        self.active_games[chat_id] = game
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

    def assign_roles_and_notify(self, chat_id, bot):
        game = self.active_games.get(chat_id)
        if not game:
            return False

        players = list(game.players.keys())
        random.shuffle(players)
        roles_list = ROLES  # DOĞRU: ROLES zaten liste

        # Rolleri sırayla dağıt
        for i, user_id in enumerate(players):
            role = roles_list[i % len(roles_list)]
            game.players[user_id]["role"] = role
            game.players[user_id]["power_used"] = False

        game.started = True
        game.joining = False
        game.round = 1
        game.power_phase = False

        # Rolleri özel mesajla gönder
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
                bot.send_message(user_id, text=text, reply_markup=markup)
            except Exception as e:
                print(f"Özel mesaj gönderilemedi {user_id}: {e}")

        # Başlangıç mesajı grup chatine
        asyncio.create_task(bot.send_message(chat_id, f"Oyun başladı! {len(players)} oyuncu katıldı. İlk tur başladı."))

        return True

game_manager = GameManager()

# /start komutu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if args and args[0].startswith("join_"):
        # Katılma isteği
        try:
            chat_id = int(args[0].split("_")[1])
        except:
            await update.message.reply_text("Geçersiz katılma isteği.")
            return

        user = update.effective_user
        success = game_manager.add_player(chat_id, user.id, user.username or user.first_name)
        if success:
            await update.message.reply_text(f"Başarıyla oyuna katıldınız!")
            # Gruba katıldı mesajı
            try:
                await context.bot.send_message(chat_id, f"{user.full_name} oyuna katıldı.")
            except Exception as e:
                print(f"Gruba katılma mesajı gönderilemedi: {e}")
        else:
            await update.message.reply_text("Oyuna zaten katılmışsınız veya oyun başlamış.")
        return

    # Normal start mesajı
    await update.message.reply_text(
        "Merhaba! Oyun botuna hoş geldiniz.\n"
        "Oyuna katılmak için grup içinde /savas komutunu kullanın."
    )

# /savas komutu: oyunu başlatmaya hazırlık
async def savas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    # Eğer oyun aktif değilse başlat
    started = game_manager.start_game(chat_id)
    if not started:
        await update.message.reply_text("Zaten bir oyun aktif!")
        return

    # Katılma butonu
    keyboard = [
        [InlineKeyboardButton("Katıl", callback_data=f"join_{chat_id}")]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Savaş oyunu başladı! Katılmak için aşağıdaki butona basın. "
        "Katılım süresi 2 dakikadır.",
        reply_markup=markup,
    )

    # 2 dakika sonra otomatik başlat
    async def auto_start():
        await asyncio.sleep(120)
        if game_manager.can_start(chat_id):
            await basla_oyunu(chat_id, context)
        else:
            await context.bot.send_message(chat_id, "Yeterli oyuncu yok, oyun iptal edildi.")
            # Oyunu temizle
            if chat_id in game_manager.active_games:
                del game_manager.active_games[chat_id]

    asyncio.create_task(auto_start())

# Oyun başlatma fonksiyonu (assign_roles_and_notify çağrılır)
async def basla_oyunu(chat_id, context):
    success = game_manager.assign_roles_and_notify(chat_id, context.bot)
    if not success:
        await context.bot.send_message(chat_id, "Oyun başlatılamadı, oyuncu yok veya oyun yok.")
    else:
        await context.bot.send_message(chat_id, "Oyun başarıyla başladı!")

# /basla komutu (oyunu manuel başlatmak için)
async def basla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if game_manager.can_start(chat_id):
        await basla_oyunu(chat_id, context)
    else:
        await update.message.reply_text("Oyunu başlatmak için yeterli oyuncu yok (5-20 kişi arası).")

# Callback query handler (Katıl butonu ve diğerleri)
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    data = query.data
    await query.answer()

    if data.startswith("join_"):
        chat_id = int(data.split("_")[1])
        success = game_manager.add_player(chat_id, user.id, user.username or user.first_name)
        if success:
            await context.bot.send_message(user.id, f"Başarıyla oyuna katıldınız! /start komutuyla başlayabilirsiniz.")
            await context.bot.send_message(chat_id, f"{user.full_name} oyuna katıldı.")
        else:
            await context.bot.send_message(user.id, "Oyuna zaten katılmışsınız veya oyun başlamış.")
    elif data == "use_power":
        await context.bot.send_message(user.id, "Güç kullanma fonksiyonu yakında eklenecek.")
    else:
        await context.bot.send_message(user.id, "Bilinmeyen buton.")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bilinmeyen komut.")

def main():
    TOKEN = os.getenv("TOKEN")
    if not TOKEN:
        print("TOKEN environment variable not set!")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("savas", savas))
    app.add_handler(CommandHandler("basla", basla))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
