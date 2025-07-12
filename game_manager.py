import asyncio
import json
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# roles.json dosyasını yükle (5-20 oyuncuya uygun olmalı)
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

    def assign_roles_and_notify(self, chat_id, bot):
        game = self.active_games.get(chat_id)
        if not game:
            return False

        players = list(game.players.keys())
        random.shuffle(players)
        roles_list = list(ROLES.values())

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
                f"💥 Gücünüz: {role.get('power_name', 'Yok')}\n"
                f"📜 Açıklama: {role.get('power_desc', '')}"
            )
            try:
                bot.send_message(user_id, text=text, reply_markup=markup)
            except Exception as e:
                print(f"Özel mesaj gönderilemedi {user_id}: {e}")

        # Başlangıç mesajı grup chatine
        asyncio.create_task(bot.send_message(chat_id, f"Oyun başladı! {len(players)} oyuncu katıldı. İlk tur başladı."))

        return True

    def alive_players(self, chat_id):
        game = self.active_games.get(chat_id)
        if not game:
            return []
        return [uid for uid, p in game.players.items() if p["alive"]]

    async def start_vote_phase(self, chat_id, context):
        game = self.active_games.get(chat_id)
        if not game or not game.started:
            await context.bot.send_message(chat_id, "Oyun başlamadı veya aktif değil.")
            return

        game.votes = {}
        game.power_phase = False

        alive = self.alive_players(chat_id)

        # Her oyuncuya DM ile oylama butonları gönder
        for user_id in alive:
            try:
                keyboard = []
                for target_id in alive:
                    if target_id == user_id:
                        continue
                    target_name = game.players[target_id]["username"]
                    keyboard.append([InlineKeyboardButton(target_name, callback_data=f"vote_{target_id}")])
                markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(
                    chat_id=user_id,
                    text="🔫 Kime oy vereceksiniz? (Kendi adınıza oy veremezsiniz.)",
                    reply_markup=markup,
                )
            except Exception as e:
                print(f"Oylama mesajı gönderilemedi {user_id}: {e}")

        # 40 saniye sonra oylamayı sonuçlandır
        game.vote_task = asyncio.create_task(self._vote_timeout(chat_id, context))

    async def _vote_timeout(self, chat_id, context):
        await asyncio.sleep(40)
        await self.finish_vote(chat_id, context)

    async def finish_vote(self, chat_id, context):
        game = self.active_games.get(chat_id)
        if not game:
            return

        tally = {}
        for vote in game.votes.values():
            tally[vote] = tally.get(vote, 0) + 1

        if not tally:
            await context.bot.send_message(chat_id, "Oylama yapılmadı, kimse elenmedi.")
            await self.next_round(chat_id, context)
            return

        max_votes = max(tally.values())
        eliminated = [uid for uid, count in tally.items() if count == max_votes]

        # Eşitlik varsa rastgele seç
        eliminated_player = random.choice(eliminated)

        self.eliminate_player(chat_id, eliminated_player)

        username = game.players[eliminated_player]["username"]
        role_name = game.players[eliminated_player]["role"]["name"]

        msg, gif = self._elimination_message(role_name, username)
        await context.bot.send_message(chat_id, f"🏳️ {msg}\n{gif}")

        await self.next_round(chat_id, context)

    def eliminate_player(self, chat_id, user_id):
        game = self.active_games.get(chat_id)
        if not game:
            return False
        if user_id in game.players:
            game.players[user_id]["alive"] = False
            return True
        return False

    def _elimination_message(self, role_name, username):
        elim_msgs = {
            "Osmanlı İmparatorluğu": (f"{username} (Osmanlı) elendi.", "https://media.giphy.com/media/gFiY5QBLqvrx2/giphy.gif"),
            "German İmparatorluğu": (f"{username} (Alman) elendi.", "https://media.giphy.com/media/5xaOcLGvzHxDKjufnLW/giphy.gif"),
            "Rusya Federasyonu": (f"{username} (Rusya) elendi.", "https://media.giphy.com/media/YQitE4YNQNahy/giphy.gif"),
            "İran": (f"{username} (İran) elendi.", "https://media.giphy.com/media/k7VVlKoZFkHG8/giphy.gif"),
            "ABD": (f"{username} (ABD) elendi.", "https://media.giphy.com/media/xT0xeJpnrWC4XWblEk/giphy.gif"),
            "Britanya": (f"{username} (Britanya) elendi.", "https://media.giphy.com/media/fxsqOYnIMEefC/giphy.gif"),
        }
        if role_name in elim_msgs:
            return elim_msgs[role_name]
        return (f"{username} ({role_name}) elendi.", "")

    async def next_round(self, chat_id, context):
        game = self.active_games.get(chat_id)
        if not game:
            return

        alive = self.alive_players(chat_id)
        if len(alive) <= 1:
            winner = game.players[alive[0]]["username"] if alive else "Kimse"
            await context.bot.send_message(chat_id, f"🎉 Oyun bitti! Kazanan: {winner}")
            del self.active_games[chat_id]
            return

        game.round += 1
        game.power_phase = True

        # Her oyuncunun power_used değerini sıfırla
        for uid in alive:
            game.players[uid]["power_used"] = False

        await context.bot.send_message(chat_id, f"{game.round}. tur başladı! Güçlerinizi kullanabilirsiniz.")

        # Güç kullanım süresi (örnek 40 sn) sonrası oylama başlat
        asyncio.create_task(self._power_phase_timeout(chat_id, context))

    async def _power_phase_timeout(self, chat_id, context):
        await asyncio.sleep(40)
        game = self.active_games.get(chat_id)
        if game:
            game.power_phase = False
            await context.bot.send_message(chat_id, "Güç kullanma süresi sona erdi, şimdi oylama başlıyor.")
            await self.start_vote_phase(chat_id, context)

    async def use_power(self, update, context, chat_id, user_id):
        game = self.active_games.get(chat_id)
        if not game or not game.started or not game.power_phase:
            await update.message.reply_text("Güç kullanma zamanı değil.")
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
        power_desc = role.get("power_desc", "Açıklama yok.")

        alive = self.alive_players(chat_id)
        keyboard = []
        for uid in alive:
            if uid == user_id:
                continue
            username = game.players[uid]["username"]
            keyboard.append([InlineKeyboardButton(username, callback_data=f"power_{uid}")])
        markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text=f"Gücünüzü kullanmak için hedef seçin: {power_name}\n{power_desc}",
            reply_markup=markup,
        )

    async def handle_callback(self, update, context):
        query = update.callback_query
        user_id = query.from_user.id
        data = query.data

        # Oyunun hangi chat_id'de olduğunu bul (kullanıcının dahil olduğu oyun)
        chat_id = None
        for cid, game in self.active_games.items():
            if user_id in game.players:
                chat_id = cid
                break
        if not chat_id:
            await query.answer("Oyunda değilsiniz.")
            return

        game = self.active_games.get(chat_id)
        if not game:
            await query.answer("Oyun bulunamadı.")
            return

        if data.startswith("vote_"):
            if not game.started or game.power_phase:
                await query.answer("Şu anda oy kullanılamaz.")
                return

            target_id = int(data.split("_")[1])

            if not game.players[user_id]["alive"]:
                await query.answer("Elendiniz, oy kullanamazsınız.")
                return

            game.votes[user_id] = target_id
            await query.answer(f"{game.players[target_id]['username']} seçildi.")
            await query.message.edit_text("Oy kullandınız, bekleyin...")

        elif data.startswith("power_"):
            if not game.started or not game.power_phase:
                await query.answer("Güç kullanılamaz.")
                return

            target_id = int(data.split("_")[1])
            player = game.players[user_id]

            if not player["alive"]:
                await query.answer("Elendiniz, güç kullanamazsınız.")
                return

            if player["power_used"]:
                await query.answer("Bu turda gücünüzü zaten kullandınız.")
                return

            # Güç kullanıldı işaretle
            player["power_used"] = True

            role = player["role"]
            power_name = role.get("power_name", "Özel Güç")
            target_name = game.players[target_id]["username"]

            # Burada güç etkisini uygula (şimdilik sadece mesaj)
            await query.answer(f"{power_name} kullanıldı hedef: {target_name}")
            await query.message.edit_text(f"Güç başarıyla kullanıldı, bekleyin...")

            # Grup sohbetine güç kullanımı mesajı
            await context.bot.send_message(
                chat_id,
                f"{player['username']} adlı oyuncu {power_name} gücünü kullandı. Hedef: {target_name}"
            )

        elif data == "use_power":
            # Güç kullanma butonuna basıldı, güç kullanımını başlat
            await self.use_power(update, context, chat_id, user_id)
            await query.answer()

        else:
            await query.answer("Bilinmeyen komut.")

    def stop_game(self, chat_id):
        if chat_id in self.active_games:
            del self.active_games[chat_id]
