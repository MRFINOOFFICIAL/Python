# commands/blackjack.py
import random
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from db import get_user, add_money, get_inventory

# ---------- Helpers ----------
def new_deck():
    ranks = ['2','3','4','5','6','7','8','9','10','J','Q','K','A']
    deck = ranks * 4
    random.shuffle(deck)
    return deck

def card_value(card: str) -> int:
    if card in ('J','Q','K'):
        return 10
    if card == 'A':
        return 11
    return int(card)

def hand_value(cards: list) -> int:
    total = sum(card_value(c) for c in cards)
    aces = cards.count('A')
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total

# Estado en memoria de partidas: user_id -> state
GAMES: dict = {}

# ---------- View ----------
class BJView(discord.ui.View):
    def __init__(self, cog, uid: int, timeout: int = 120):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.uid = uid

        # Buttons: Hit, Stand, Double
        btn_hit = discord.ui.Button(label="Hit", style=discord.ButtonStyle.primary)
        btn_hit.callback = self._cb_hit
        self.add_item(btn_hit)

        btn_stand = discord.ui.Button(label="Stand", style=discord.ButtonStyle.secondary)
        btn_stand.callback = self._cb_stand
        self.add_item(btn_stand)

        btn_double = discord.ui.Button(label="Double", style=discord.ButtonStyle.danger)
        btn_double.callback = self._cb_double
        self.add_item(btn_double)

    async def _cb_hit(self, interaction: discord.Interaction):
        await self.cog._player_hit(interaction, self.uid)

    async def _cb_stand(self, interaction: discord.Interaction):
        await self.cog._player_stand(interaction, self.uid)

    async def _cb_double(self, interaction: discord.Interaction):
        await self.cog._player_double(interaction, self.uid)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.uid

    async def on_timeout(self):
        # disable buttons (safe type-check)
        for child in list(self.children):
            if isinstance(child, discord.ui.Button):
                try:
                    child.disabled = True
                except Exception:
                    pass
        # try to edit the message stored in game state to show disabled buttons
        state = GAMES.get(self.uid)
        if state:
            msg = state.get("message")
            if isinstance(msg, discord.Message):
                try:
                    await msg.edit(view=self)
                except Exception:
                    pass

# ---------- Cog ----------
class BlackjackCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # hybrid_command -> crea tanto prefix como slash (se registra al sync)
    @commands.hybrid_command(name="blackjack", description="Juega una mano de Blackjack")
    @app_commands.describe(bet="Cantidad a apostar")
    async def blackjack(self, ctx: commands.Context, bet: int):
        """
        Usa !blackjack <bet> o /blackjack <bet>
        """
        is_interaction = getattr(ctx, "interaction", None) is not None

        # si es slash, defer la respuesta para poder usar followup
        if is_interaction:
            await ctx.interaction.response.defer()
            async def send_fn(**kw):
                return await ctx.interaction.followup.send(**kw)
        else:
            async def send_fn(**kw):
                return await ctx.send(**kw)

        await self._start_game(ctx, ctx.author, bet, send_fn, is_interaction)

    async def _start_game(self, ctx_or_ctxobj, user, bet: int, send_fn, is_interaction: bool = False):
        uid = user.id

        # guard: no partida en curso
        if uid in GAMES:
            return await send_fn(content="❌ Ya tienes una partida en curso. Termínala antes de empezar otra.")

        # validar apuesta
        db_user = await get_user(uid)
        if bet <= 0 or db_user["dinero"] < bet:
            return await send_fn(content="❌ No tienes suficiente dinero o la apuesta es inválida.")

        # inicializar
        deck = new_deck()
        player = [deck.pop(), deck.pop()]
        dealer = [deck.pop(), deck.pop()]

        inv = await get_inventory(uid)
        items_low = [i["item"].lower() for i in inv]
        mecha_x2 = any(it == "x2 de dinero de mecha" for it in items_low)
        danza = any(it == "danza de saviteto" for it in items_low)

        view = BJView(self, uid, timeout=120)

        state = {
            "deck": deck,
            "player": player,
            "dealer": dealer,
            "bet": bet,
            "mecha_x2": mecha_x2,
            "danza": danza,
            "stage": "playing",
            "message": None,
            "view": view
        }
        GAMES[uid] = state

        embed = discord.Embed(
            title="🃏 Blackjack",
            description=f"Apuesta: **{bet}💰**\nUsa los botones para jugar.",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Tu mano", value=f"{', '.join(player)} — {hand_value(player)}", inline=False)
        embed.add_field(name="Mano del dealer", value=f"{dealer[0]}, ❓", inline=False)
        embed.set_footer(text="Opciones: Hit = Pedir carta, Stand = Plantarte, Double = Duplicar apuesta (solo en primera jugada)")

        sent = await send_fn(embed=embed, view=view)
        # guardar mensaje y view en estado
        try:
            state["message"] = sent if isinstance(sent, discord.Message) else None
        except Exception:
            state["message"] = None
        state["view"] = view
        GAMES[uid] = state

    # ---------- Player actions ----------
    async def _player_hit(self, interaction: discord.Interaction, uid: int):
        state = GAMES.get(uid)
        if not state or state.get("stage") != "playing":
            return await interaction.response.send_message("❌ Partida no encontrada o ya terminada.", ephemeral=True)

        deck = state["deck"]
        player = state["player"]
        player.append(deck.pop())
        pv = hand_value(player)

        # preparar embed actualizado
        embed = discord.Embed(title="🃏 Blackjack", color=discord.Color.blurple())
        embed.add_field(name="Tu mano", value=f"{', '.join(player)} — {pv}", inline=False)
        embed.add_field(name="Mano del dealer", value=f"{state['dealer'][0]}, ❓", inline=False)

        view = state.get("view")

        # si se pasó -> perder
        if pv > 21:
            state["stage"] = "finished"
            bet = state["bet"]
            # restar apuesta al jugador
            await add_money(uid, -bet)
            text = f"💥 Te pasaste con {pv}. Perdiste {bet}💰."

            # deshabilitar botones de forma segura
            if view:
                for child in list(view.children):
                    if isinstance(child, discord.ui.Button):
                        try:
                            child.disabled = True
                        except Exception:
                            pass

            # editar mensaje original
            try:
                await interaction.response.edit_message(embed=embed, view=view, content=text)
            except Exception:
                # fallback si no se puede editar
                await interaction.response.send_message(content=text)
            GAMES.pop(uid, None)
            return

        # continuar la partida (actualizar mensaje)
        state["player"] = player
        try:
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception:
            await interaction.response.send_message(embed=embed)

    async def _player_stand(self, interaction: discord.Interaction, uid: int):
        state = GAMES.get(uid)
        if not state or state.get("stage") != "playing":
            return await interaction.response.send_message("❌ Partida no encontrada o ya terminada.", ephemeral=True)

        deck = state["deck"]
        player = state["player"]
        dealer = state["dealer"]
        bet = state["bet"]

        # dealer juega
        while hand_value(dealer) < 17:
            dealer.append(deck.pop())

        pv = hand_value(player)
        dv = hand_value(dealer)

        win = None
        reason = ""

        if dv > 21:
            win = True
            reason = f"El dealer se pasó ({dv})."
        elif pv > dv:
            win = True
            reason = f"Tú {pv} vs Dealer {dv}."
        elif pv == dv:
            win = None
            reason = f"Empate: {pv}."
        else:
            win = False
            reason = f"Tú {pv} vs Dealer {dv}."

        total_payout = 0
        result_text = ""

        if win is True:
            # payout: devolver apuesta + ganancia igual a la apuesta (net +bet)
            # En esta implementación: sumamos la ganancia neta al saldo
            payout = bet
            # blackjack natural?
            if len(player) == 2 and hand_value(player) == 21:
                bonus = int(bet * 1.5)  # standard 3:2
                if state["danza"]:
                    bonus = int(bonus * 1.15)
                payout += bonus
            # aplicar mecha_x2 (duplica solo las ganancias)
            if state["mecha_x2"]:
                payout *= 2
            total_payout = payout
            await add_money(uid, total_payout)
            result_text = f"✅ Ganaste {total_payout}💰! ({reason})"
        elif win is None:
            total_payout = 0
            result_text = f"➖ Empate. Recuperas tu apuesta ({bet}💰)."
            # No hacemos cambios en dinero dado que la apuesta no se quitó al inicio.
        else:
            total_payout = -bet
            await add_money(uid, total_payout)
            result_text = f"❌ Perdiste {bet}💰. ({reason})"

        # finalizar
        state["stage"] = "finished"
        view = state.get("view")
        # deshabilitar botones
        if view:
            for child in list(view.children):
                if isinstance(child, discord.ui.Button):
                    try:
                        child.disabled = True
                    except Exception:
                        pass

        embed = discord.Embed(
            title="🃏 Blackjack — Resultado",
            color=(discord.Color.green() if total_payout > 0 else discord.Color.red())
        )
        embed.add_field(name="Tu mano", value=f"{', '.join(player)} — {pv}", inline=False)
        embed.add_field(name="Mano del dealer", value=f"{', '.join(dealer)} — {dv}", inline=False)
        content = result_text + (("\n\n(Se aplicaron tus items.)") if (state["mecha_x2"] or state["danza"]) else "")

        try:
            await interaction.response.edit_message(embed=embed, view=view, content=content)
        except Exception:
            await interaction.response.send_message(embed=embed, content=content)

        GAMES.pop(uid, None)

    async def _player_double(self, interaction: discord.Interaction, uid: int):
        state = GAMES.get(uid)
        if not state or state.get("stage") != "playing":
            return await interaction.response.send_message("❌ Partida no encontrada o ya terminada.", ephemeral=True)

        # solo si tiene exactamente 2 cartas
        if len(state["player"]) != 2:
            return await interaction.response.send_message("❌ Double solo se permite en la primera jugada (2 cartas).", ephemeral=True)

        bet = state["bet"]
        db_user = await get_user(uid)
        if db_user["dinero"] < bet:
            return await interaction.response.send_message("❌ No tienes dinero para doblar la apuesta.", ephemeral=True)

        # cobrar apuesta adicional
        await add_money(uid, -bet)
        state["bet"] = bet * 2

        # dar una carta al jugador y usar la lógica de stand (se asume que ya se ha pagado la segunda mitad)
        deck = state["deck"]
        state["player"].append(deck.pop())

        # llamar a stand para resolver la mano
        await self._player_stand(interaction, uid)

# ---------- setup ----------
async def setup(bot):
    cog = BlackjackCog(bot)
    await bot.add_cog(cog)
    # no agregamos manualmente app command: hybrid_command se registra en sync del bot

