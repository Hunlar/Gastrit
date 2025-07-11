import asyncio
import json
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

# roles.json dosyasını yükle
with open("roles.json", encoding="utf-8") as f:
    ROLES = json.load(f)

class GameManager:
    def __init__(self):
        self.active_games = {}  # chat_id: GameData

    class GameData:
        def __init__(self):
            self.players = {}  # user_id: {"username": str, "role": dict, "alive": bool, "power_used": bool}
            self.started = False
            self.round = 0
            self.votes = {}  # user_id: target_user_id
            self.vote_task = None
            self.power_task = None

    def start_game(self, chat_id):
        if chat_id in self.active_games:
            return False
        self.active_games[chat_id] = self.GameData()
        return True

    def add_player(self, chat_id, user_id, username):
        game = self.active_games.get(chat_id)
        if not game or game.started:
            return False
        if user_id not in game.players:
            game.players[user_id] = {"username": username, "role": None, "alive": True, "power_used": False}
            return True
        return False

    def assign_roles(self, chat_id):
        game = self.active_games.get(chat_id)
        if not game:
            return False
        players = list(game.players.keys())
        random.shuffle(players)
        roles_list = list(ROLES.values())
        # Rolleri eşleştir (en az oyuncu sayısı kadar rol var kabulüyle)
        for i, user_id in enumerate(players):
            role = roles_list[i % len(roles_list)]
            game.players[user_id]["role"] = role
            game.players[user_id]["power_used"] = False
        game.started = True
        game.round = 1
        return True

    def get_player_role(self, chat_id, user_id):
        game = self.active_games.get(chat_id)
        if not game:
            return None
        player = game.players.get(user_id)
        if not player:
            return None
        return player["role"]

    def is_alive(self, chat_id, user_id):
        game = self.active_games.get(chat_id)
        if not game:
            return False
        player = game.players.get(user_id)
        return player and player["alive"]

    def eliminate_player(self, chat_id, user_id):
        game = self.active_games.get(chat_id)
        if not game:
            return False
        if user_id in game.players:
            game.players[user_id]["alive"] = False
            return True
        return False

    def alive_players(self, chat_id):
        game = self.active_games.get(chat_id)
        if not game:
            return []
        return [uid for uid, p in game.players.items() if p["alive"]]

    # --- OYLAMA ve GÜÇ KULLANIMI ---

    async def start_vote(self, update: Update, context: CallbackContext, chat_id: int):
        game = self.active_games.get(chat_id)
        if not game or not game.started:
            await update.message.reply_text("Oyun başlamadı.")
            return

        alive = self.alive_players(chat_id)
        game.votes = {}

        # Her oyuncuya DM at, oy kullanması için butonları gönder
        for user_id in alive:
            try:
                role = game.players[user_id]["role"]
                keyboard = []
                for target_id in alive:
                    if target_id == user_id:
                        continue
                    target_name = game.players[target_id]["username"]
                    keyboard.append([InlineKeyboardButton(target_name, callback_data=f"vote_{target_id}")])
                markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"Oylama zamanı! Kime oy vereceksin? (Rollerin gücünü kullanabilirsin.)",
                    reply_markup=markup,
                )
            except Exception as e:
                print(f"Mesaj gönderilemedi: {e}")

        # 40 saniye bekle oylama için
        game.vote_task = asyncio.create_task(self._wait_vote_timeout(chat_id, context))

    async def _wait_vote_timeout(self, chat_id, context: CallbackContext):
        await asyncio.sleep(40)
        await self.finish_vote(chat_id, context)

    async def finish_vote(self, chat_id, context: CallbackContext):
        game = self.active_games.get(chat_id)
        if not game:
            return
        # Oyları say, en çok oy alanı bul
        tally = {}
        for vote in game.votes.values():
            tally[vote] = tally.get(vote, 0) + 1

        if not tally:
            await context.bot.send_message(chat_id, "Oylama sonucu: Oy kullanma olmadı, kimse elenmedi.")
            return

        max_votes = max(tally.values())
        eliminated = [uid for uid, count in tally.items() if count == max_votes]

        # Eğer birden fazla ise eşitlik var, rastgele birini seç
        eliminated_player = random.choice(eliminated)

        # Oyuncuyu el
        self.eliminate_player(chat_id, eliminated_player)
        username = game.players[eliminated_player]["username"]
        role_name = game.players[eliminated_player]["role"]["name"]

        # Elenen ülkeye göre özel mesaj ve gif gönder
        msg, gif = self._elimination_message(role_name, username)
        await context.bot.send_message(chat_id, f"{msg}\n{gif}")

        game.round += 1

        # Sonraki aşama için mesaj
        await context.bot.send_message(chat_id, f"{game.round}. tur başladı! Güçlerinizi kullanabilir veya oylamaya devam edebilirsiniz.")

        # Güç kullanım süreci başlatılabilir buraya eklenebilir

    def _elimination_message(self, role_name, username):
        # Örnek mesajlar, rol adına göre dönecek
        elim_msgs = {
            "Osmanlı İmparatorluğu": (f"Kim bu kadar borç edindi! {username} adlı oyuncu Osmanlı elendi.", "https://media.giphy.com/media/gFiY5QBLqvrx2/giphy.gif"),
            "German İmparatorluğu": (f"Hitler’i Hitler’e benzemek suçundan kazığa oturttular. {username} elendi.", "https://media.giphy.com/media/5xaOcLGvzHxDKjufnLW/giphy.gif"),
            "Rusya Federasyonu": (f"Soğuk hava şartları canına tak eden Putin Muğla’ya yerleşti. {username} elendi.", "https://media.giphy.com/media/YQitE4YNQNahy/giphy.gif"),
            "İran": (f"İran Devrim başkanı annesini bombaladı. {username} elendi.", "https://media.giphy.com/media/k7VVlKoZFkHG8/giphy.gif"),
            "ABD": (f"İngiliz boku yiyen Tramp kanserden öldü. {username} elendi.", "https://media.giphy.com/media/xT0xeJpnrWC4XWblEk/giphy.gif"),
            "Britanya": (f"İngilizler Ais hastalığına yakalanan kraliçe Elizabeth'i twörk ata ata uğurladı. {username} elendi.", "https://media.giphy.com/media/fxsqOYnIMEefC/giphy.gif"),
        }
        if role_name in elim_msgs:
            return elim_msgs[role_name]
        else:
            return (f"Bir bok daha kaydı: {role_name} ({username}) elendi.", "")

    async def use_power(self, update: Update, context: CallbackContext, chat_id: int, user_id: int):
        # Kullanıcının gücü kullanma hakkı kontrolü
        game = self.active_games.get(chat_id)
        if not game:
            await update.message.reply_text("Oyun bulunamadı.")
            return

        player = game.players.get(user_id)
        if not player or not player["alive"]:
            await update.message.reply_text("Oyunda değilsiniz veya elendiniz.")
            return

        if player["power_used"]:
            await update.message.reply_text("Bu turda gücünüzü zaten kullandınız.")
            return

        role = player["role"]
        power_name = role.get("power_name", "Özel Güç")
        power_desc = role.get("power_desc", "Özel güç açıklaması yok.")
        power_targets = role.get("power_targets", [])

        if not power_targets:
            await update.message.reply_text(f"{power_name} için geçerli hedef yok.")
            return

        # Kullanıcıya hedef seçtirmek için butonlar oluştur
        keyboard = []
        alive = self.alive_players(chat_id)
        for uid in alive:
            if uid == user_id:
                continue
            if uid in power_targets or not power_targets:
                username = game.players[uid]["username"]
                keyboard.append([InlineKeyboardButton(username, callback_data=f"power_{uid}")])
        markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text=f"Gücünüzü kullanmak için hedef seçin: {power_name}\n{power_desc}",
            reply_markup=markup,
        )

    # Callback query handler metodu (main.py'den callback_query_handler içerisinde çağrılacak)
    async def handle_callback(self, update: Update, context: CallbackContext):
        query = update.callback_query
        user_id = query.from_user.id
        chat_id = query.message.chat_id  # Bu genelde grup chat id olur, DM ise user_id olur
        data = query.data

        # Hangi oyunda olduğuna karar ver
        # Şimdilik 1 oyun varsayalım aktif
        # Geliştirilirse chat_id üzerinden veya user_id üzerinden oyun bulunabilir

        # vote_1234 şeklinde callback
        if data.startswith("vote_"):
            target_id = int(data.split("_")[1])
            game = None
            for g in self.active_games.values():
                if user_id in g.players:
                    game = g
                    break
            if not game:
                await query.answer("Oyunda değilsiniz.")
                return
            if not game.players[user_id]["alive"]:
                await query.answer("Elendiniz, oy kullanamazsınız.")
                return
            game.votes[user_id] = target_id
            await query.answer(f"{game.players[target_id]['username']} seçildi.")
            await query.message.edit_text("Oyun kullanıldı, bekleyin...")
            return

        # power_1234 şeklinde callback
        if data.startswith("power_"):
            target_id = int(data.split("_")[1])
            game = None
            for g in self.active_games.values():
                if user_id in g.players:
                    game = g
                    break
            if not game:
                await query.answer("Oyunda değilsiniz.")
                return
            if not game.players[user_id]["alive"]:
                await query.answer("Elendiniz, güç kullanamazsınız.")
                return

            # Gücü kullandık işaretle
            game.players[user_id]["power_used"] = True
            role = game.players[user_id]["role"]
            power_name = role.get("power_name", "Özel Güç")

            # Burada güç etkisi uygulanmalı, şimdilik sadece mesaj
            await query.answer(f"{power_name} kullanıldı hedef: {game.players[target_id]['username']}")
            await query.message.edit_text(f"Güç başarıyla kullanıldı, bekleyin...")

            # Güç kullanıldığında chat mesajı at (örnek)
            chat_id = None
            for cid, g in self.active_games.items():
                if user_id in g.players:
                    chat_id = cid
                    break
            if chat_id:
                # Örnek mesaj ve gif (bunu rol bilgisine göre değiştir)
                msg = f"{role['name']} özel gücünü kullandı: {power_name} hedef: {game.players[target_id]['username']}"
                gif = role.get("power_gif", "")
                await context.bot.send_message(chat_id, f"{msg}\n{gif}")

            return

    # Ek yardımcılar...
