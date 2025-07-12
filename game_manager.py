import asyncio
import json
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

with open("roles.json", encoding="utf-8") as f:
    ROLES = json.load(f)

class GameManager:
    def __init__(self):
        self.active_games = {}  # chat_id: GameData

    class GameData:
        def __init__(self):
            self.players = {}  # user_id: {"username": str, "role": dict, "alive": bool, "power_used": bool}
            self.started = False
            self.joining = False
            self.join_task = None
            self.round = 0
            self.votes = {}

    def start_game(self, chat_id):
        if chat_id in self.active_games:
            # Zaten oyun varsa False döner
            return False
        self.active_games[chat_id] = self.GameData()
        self.active_games[chat_id].joining = True
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

    async def start_join_period(self, chat_id, context: CallbackContext):
        """2 dakika katılım süresi başlatır, her 30 saniyede bildirim yapar"""
        game = self.active_games.get(chat_id)
        if not game or not game.joining:
            return

        total_time = 120
        intervals = [90, 60, 30]

        for remaining in intervals:
            await asyncio.sleep(30)
            await context.bot.send_message(
                chat_id,
                f"⏳ Oyuna katılım devam ediyor, kalan süre: {remaining} saniye."
            )
        # Süre doldu
        game.joining = False
        # Oyuncu sayısı kontrolü ve başlatma bildirimi
        if self.can_start(chat_id):
            await context.bot.send_message(chat_id, f"✅ Katılım tamamlandı, {len(game.players)} oyuncu ile oyun başlıyor!")
            self.assign_roles(chat_id)
            game.started = True
            game.round = 1
            # Burada oyuna devam işlemi yapılabilir (mesaj, oylama vs)
        else:
            await context.bot.send_message(chat_id, f"⚠️ Oyuncu sayısı yeterli değil ({len(game.players)}). Oyun iptal edildi.")
            del self.active_games[chat_id]

    def assign_roles(self, chat_id):
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
        return True

    async def force_start(self, chat_id, context: CallbackContext):
        """Oyunu erkenden başlatır, yeterli oyuncu varsa"""
        game = self.active_games.get(chat_id)
        if not game or not game.joining:
            await context.bot.send_message(chat_id, "Katılım süreci başlamamış veya zaten oyun başladı.")
            return False

        if not self.can_start(chat_id):
            await context.bot.send_message(chat_id, f"En az 5, en fazla 20 oyuncu olmalı. Şu an: {len(game.players)}")
            return False

        game.joining = False
        self.assign_roles(chat_id)
        game.started = True
        game.round = 1
        await context.bot.send_message(chat_id, f"✅ Oyuncu sayısı yeterli, oyun erkenden başlatıldı! {len(game.players)} oyuncu ile başlayalım.")
        # Burada oyuna devam işlemi yapılabilir (mesaj, oylama vs)
        return True
