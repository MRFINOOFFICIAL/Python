# commands/explore.py
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View
from db import add_item_to_user, get_inventory, remove_item
import random
from typing import Tuple, List
from cache import set_buff, get_buff, clear_buff

# ---------- Tabla de objetos (ampliada) ----------
# Formato: (nombre, rareza, usos)
LOOT_TABLE: List[Tuple[str, str, int]] = [
    ("Cinta adhesiva", "comun", 1),
    ("Botella de sedante", "comun", 1),
    ("Cuchillo oxidado", "raro", 3),
    ("Pistola vieja", "epico", 5),
    ("Botiquín", "comun", 1),
    ("Arma blanca artesanal", "raro", 3),
    ("Palo golpeador de parejas felices", "epico", 5),
    ("Savi peluche", "epico", 5),
    ("Hélice de ventilador", "comun", 1),
    ("Aconsejante Fantasma", "epico", 5),
    ("ID falso", "raro", 3),
    ("Máscara de Xfi", "epico", 5),

    # Nuevos pedidos (del usuario + extras)
    ("Bastón de Staff", "raro", 4),
    ("Teléfono", "comun", 1),
    ("Chihuahua", "raro", 2),
    ("Mecha Enojado", "epico", 6),
    ("Linterna", "comun", 1),
    ("Llave Maestra", "epico", 1),

    # +10 objetos adicionales para variedad
    ("Anillo oxidado", "comun", 1),
    ("Mapa antiguo", "raro", 1),
    ("Gafas de soldador", "raro", 1),
    ("Caja de cerillas", "comun", 1),
    ("Receta secreta", "epico", 1),
    ("Núcleo energético", "legendario", 1),
    ("Fragmento Omega", "maestro", 1),
    ("Traje ritual", "legendario", 1),
    ("Placa de identificación", "raro", 1),
    ("Cable USB", "comun", 1),
    ("Garrafa de aceite", "comun", 1),
    ("Guitarra rota", "raro", 1),
]

# Pesos de aparición (misma longitud que LOOT_TABLE)
WEIGHTS = [
    40,40,10,5,30,15,5,5,25,5,10,5,
    8,30,15,6,20,4,
    35,12,10,40,15,2,1,2,10,50,35,18
]
assert len(WEIGHTS) == len(LOOT_TABLE), "Ajusta WEIGHTS para que coincida con LOOT_TABLE"

# ---------- Cofres ----------
CHEST_CHANCE = 0.12  # probabilidad de que aparezca un cofre en vez de objeto
CHEST_RARITY_WEIGHTS = {"comun":60,"raro":25,"epico":10,"legendario":4,"maestro":1}
CHEST_YIELD = {"comun":(1,1),"raro":(1,2),"epico":(1,2),"legendario":(2,3),"maestro":(2,4)}

# Prob de que un cofre esté sellado (solo abrible con Llave Maestra)
SEALED_PROB = {"epico": 0.03, "legendario": 0.15, "maestro": 0.65}

# Si se usa llave maestra en cofres sellados, ¿se consume la llave? (True/False)
CONSUME_KEY_ON_SEALED = True

# Emojis por rareza (para embeds/anim)
RARITY_EMOJI = {"comun":"⚪","raro":"🔵","epico":"🟣","legendario":"🟠","maestro":"🔶"}

# Stats (categoria y poder) para objetos — usados por rob y para describir usos.
ITEM_STATS = {
    "cinta adhesiva":      {"categoria": "herramientas", "poder": 3},
    "botella de sedante":  {"categoria": "quimicos",    "poder": 6},
    "cuchillo oxidado":    {"categoria": "arma",       "poder": 18},
    "pistola vieja":       {"categoria": "arma",       "poder": 35},
    "botiquín":            {"categoria": "salud",      "poder": 2},
    "arma blanca artesanal":{"categoria":"arma",       "poder": 25},
    "palo golpeador de parejas felices": {"categoria":"arma","poder":30},
    "savi peluche":        {"categoria": "engano",     "poder": 10},
    "hélice de ventilador":{"categoria": "herramientas","poder": 8},
    "aconsejante fantasma": {"categoria":"engano",     "poder": 30},
    "id falso":            {"categoria": "engano",     "poder": 22},
    "máscara de xfi":      {"categoria": "engano",     "poder": 35},
    "bastón de staff":     {"categoria": "herramientas","poder": 28},
    "teléfono":            {"categoria": "tecnologia", "poder": 12},
    "chihuahua":           {"categoria": "mascota",    "poder": 5},
    "mecha enojado":       {"categoria": "arma",       "poder": 40},
    "linterna":            {"categoria": "herramientas","poder": 7},
    "llave maestra":       {"categoria": "herramientas","poder": 0},
    # extras: default handled later
}

def pick_chest_rarity() -> str:
    keys = list(CHEST_RARITY_WEIGHTS.keys())
    weights = list(CHEST_RARITY_WEIGHTS.values())
    return random.choices(keys, weights=weights, k=1)[0]

def pick_loot_from_rarity(rarity: str, n: int) -> List[Tuple[str,str,int]]:
    pool = [x for x in LOOT_TABLE if x[1].lower() == rarity.lower()]
    if not pool:
        if rarity == "maestro":
            pool = [x for x in LOOT_TABLE if x[1].lower() in ("maestro","legendario","epico")]
        elif rarity == "legendario":
            pool = [x for x in LOOT_TABLE if x[1].lower() in ("legendario","epico","raro")]
    if not pool:
        pool = LOOT_TABLE.copy()
    return [random.choice(pool) for _ in range(n)]

def has_item_in_inv(inv, name_substr: str) -> bool:
    ns = name_substr.lower()
    return any(ns == i["item"].lower() for i in inv)

def find_item_id_by_name(inv, name_substr: str):
    ns = name_substr.lower()
    for i in inv:
        if ns == i["item"].lower():
            return i["id"]
    return None

# ---------- Views ----------
class ReplaceView(View):
    def __init__(self, user_id: int, new_item, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.user_id = int(user_id)
        self.new_item = new_item  # tuple (name, rarity, usos)
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    async def on_timeout(self):
        for child in self.children:
            try:
                child.disabled = True
            except Exception:
                pass
        if self.message:
            try:
                await self.message.edit(content="⌛ Tiempo terminado, botones desactivados.", view=self)
            except Exception:
                pass

class ChestOpenView(View):
    def __init__(self, user_id: int, chest_rarity: str, yielding: Tuple[int,int], sealed: bool=False, timeout: int = 30):
        super().__init__(timeout=timeout)
        self.user_id = int(user_id)
        self.chest_rarity = chest_rarity
        self.yielding = yielding
        self.message = None
        self.opened = None  # True=open, False=ignored, None=timeout
        self.sealed = sealed

        btn_open = Button(label="Abrir cofre", style=discord.ButtonStyle.success)
        btn_ignore = Button(label="Ignorar", style=discord.ButtonStyle.secondary)

        async def open_cb(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                return await interaction.response.send_message("❌ Solo el que encontró el cofre puede abrirlo.", ephemeral=True)
            self.opened = True
            await interaction.response.defer()
            self.stop()

        async def ignore_cb(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                return await interaction.response.send_message("❌ Solo el que encontró el cofre puede ignorarlo.", ephemeral=True)
            self.opened = False
            await interaction.response.edit_message(content="Has decidido ignorar el cofre.", view=None)
            self.stop()

        btn_open.callback = open_cb
        btn_ignore.callback = ignore_cb
        self.add_item(btn_open)
        self.add_item(btn_ignore)

    async def on_timeout(self):
        for child in self.children:
            try:
                child.disabled = True
            except Exception:
                pass
        if self.message:
            try:
                await self.message.edit(content="⌛ Tiempo terminado. Cofre perdido.", view=self)
            except Exception:
                pass

# ---------- Cog ----------
class ExploreCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="explore")
    @commands.cooldown(1, 25, commands.BucketType.user)
    async def explore_prefix(self, ctx):
        await self._do_explore(ctx.author, send_fn=lambda **kw: ctx.send(**kw), author_ctx=ctx)

    async def explore_slash(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._do_explore(interaction.user, send_fn=lambda **kw: interaction.followup.send(**kw), author_ctx=interaction)

    async def _do_explore(self, user, send_fn, author_ctx):
        # check if user has Linterna in inventory (boosts chest/item rare chances)
        inv = await get_inventory(user.id)
        has_linterna = has_item_in_inv(inv, "linterna")

        # decide chest vs item (linterna slightly increases chest chance)
        chest_chance = CHEST_CHANCE + (0.05 if has_linterna else 0.0)
        if random.random() < chest_chance:
            # cofre encontrado
            chest_rarity = pick_chest_rarity()

            # possibility sealed
            sealed = False
            if chest_rarity in SEALED_PROB and random.random() < SEALED_PROB[chest_rarity]:
                sealed = True

            # view
            yield_min, yield_max = CHEST_YIELD.get(chest_rarity, (1,1))
            embed = discord.Embed(
                title=f"{RARITY_EMOJI.get(chest_rarity,'🎁')} ¡Has encontrado un cofre {chest_rarity.capitalize()}!",
                description=f"{user.mention}, encontraste un **cofre {chest_rarity.capitalize()}**.\n\n"
                            f"{'🔐 Está sellado (requiere Llave Maestra).' if sealed else 'Pulsa Abrir cofre para abrirlo (tiempo limitado).'}",
                color=discord.Color.gold() if chest_rarity in ("epico","legendario","maestro") else discord.Color.blurple()
            )
            view = ChestOpenView(user.id, chest_rarity, (yield_min, yield_max), sealed=sealed, timeout=30)
            sent = await send_fn(embed=embed, view=view)
            try:
                view.message = sent if isinstance(sent, discord.Message) else None
            except Exception:
                view.message = None

            # wait for user to press
            await view.wait()

            # if not opened (ignore or timeout)
            if view.opened is None:
                return
            if not view.opened:
                return

            # If sealed, verify llave maestra
            inv_now = await get_inventory(user.id)
            key_id = find_item_id_by_name(inv_now, "llave maestra")
            if sealed and not key_id:
                # no key
                await (view.message.edit(content="🔒 El cofre estaba sellado y no tienes Llave Maestra. No puedes abrirlo.", view=None) if view.message else send_fn(content="🔒 El cofre estaba sellado y no tienes Llave Maestra."))
                return
            # if sealed and has key -> consume optionally
            if sealed and key_id and CONSUME_KEY_ON_SEALED:
                try:
                    await remove_item(user.id, key_id)
                except Exception:
                    pass

            # animation: editar mensaje mostrando apertura
            try:
                if view.message:
                    await view.message.edit(content="Abriendo cofre... ░░░", embed=None, view=None)
                    await asyncio.sleep(0.7)
                    await view.message.edit(content="Abriendo cofre... ▓░░", embed=None, view=None)
                    await asyncio.sleep(0.7)
                    await view.message.edit(content="Abriendo cofre... ▓▓░", embed=None, view=None)
                    await asyncio.sleep(0.7)
                    await view.message.edit(content="Abriendo cofre... ▓▓▓", embed=None, view=None)
                    await asyncio.sleep(0.6)
            except Exception:
                # fallback silencioso
                pass

            # compute yield
            n = random.randint(yield_min, yield_max)
            # if linterna and chest rare/epic/legendario, upgrade one item
            if has_linterna and chest_rarity in ("raro","epico","legendario"):
                n = min(n+1, CHEST_YIELD.get(chest_rarity, (1,4))[1])

            # If sealed + user used key (and CONSUME_KEY_ON_SEALED False) we didn't consume; otherwise consumed above.
            picks = pick_loot_from_rarity(chest_rarity, n)
            added_names = []
            for name, rarity, usos in picks:
                # fill category/power from ITEM_STATS if exists
                key = name.lower()
                stats = ITEM_STATS.get(key, {})
                categoria = stats.get("categoria", "desconocido")
                poder = stats.get("poder", 0)
                await add_item_to_user(user.id, name, rarity, usos=usos, durabilidad=100, categoria=categoria, poder=poder)
                added_names.append(f"{name} ({rarity})")

                # special immediate effect for some non-weapon items
                if key == "telefono":
                    # Dar bonus de tiempo para la siguiente pregunta minijuego (6s)
                    set_buff(user.id, "telefono_extra_time", 6)
                if key == "chihuahua":
                    # chihuahua da una pequeña bonificación de monedas inmediata
                    try:
                        await add_item_to_user(user.id, "Moneda de compañía", "comun", usos=1, durabilidad=100, categoria="consumible", poder=0)
                    except Exception:
                        pass

            result_text = "Has abierto el cofre y obtuviste:\n" + "\n".join(f"- {x}" for x in added_names)
            try:
                if view.message:
                    await view.message.edit(content=result_text, embed=None, view=None)
                else:
                    await send_fn(content=result_text)
            except Exception:
                await send_fn(content=result_text)
            return

        # no cofre -> item normal
        item = random.choices(LOOT_TABLE, weights=WEIGHTS, k=1)[0]
        name, rarity, usos = item
        inv = await get_inventory(user.id)

        # map stats
        ks = name.lower()
        stats = ITEM_STATS.get(ks, {})
        categoria = stats.get("categoria", "desconocido")
        poder = stats.get("poder", 0)

        # If inventario con espacio
        if len(inv) < 3:
            await add_item_to_user(user.id, name, rarity, usos=usos, durabilidad=100, categoria=categoria, poder=poder)
            embed = discord.Embed(
                title=f"{RARITY_EMOJI.get(rarity,'') } 🌲 Exploración",
                description=f"{user.mention} encontraste **{name}** ({rarity})!",
                color=discord.Color.teal()
            )
            embed.set_footer(text="Sigue explorando para encontrar objetos raros y cofres.")
            # Special immediate effects for non-weapons
            if ks == "linterna":
                # set a 24h boost that increases chest chance (example)
                set_buff(user.id, "linterna_boost_until", asyncio.get_event_loop().time() + 3600*24)
                embed.add_field(name="Uso especial", value="🪄 La Linterna aumenta ligeramente tus probabilidades de cofres/objetos raros durante 24h.", inline=False)
            if ks == "telefono":
                set_buff(user.id, "telefono_extra_time", 6)
                embed.add_field(name="Uso especial", value="📱 Teléfono: +6s en la próxima pregunta de trabajo.", inline=False)
            if ks == "chihuahua":
                # chihuahua da una moneda especial al encontrarlo
                embed.add_field(name="Mascota", value="🐶 Chihuahua: te acompaña y te dio una moneda de compañía.", inline=False)
            await send_fn(embed=embed)
            return

        # inventario lleno -> ofrecer reemplazar
        embed = discord.Embed(
            title="⚠️ Inventario lleno",
            description=f"{user.mention}, encontraste **{name}** ({rarity}). Selecciona un objeto para reemplazarlo:",
            color=discord.Color.orange()
        )
        view = ReplaceView(user.id, (name, rarity, usos))
        for i in inv:
            btn = Button(label=i["item"][:80], style=discord.ButtonStyle.danger)
            async def cb(interaction: discord.Interaction, item_id=i["id"], item_name=i["item"]):
                if interaction.user.id != user.id:
                    return await interaction.response.send_message("❌ Solo quien encontró el objeto puede reemplazar.", ephemeral=True)
                await remove_item(interaction.user.id, item_id)
                # cuando agregamos, incluimos categoria/poder
                await add_item_to_user(interaction.user.id, name, rarity, usos=usos, durabilidad=100, categoria=categoria, poder=poder)
                await interaction.response.edit_message(content=f"Has reemplazado **{item_name}** con **{name}**!", embed=None, view=None)
            btn.callback = cb
            view.add_item(btn)

        sent = await send_fn(embed=embed, view=view)
        try:
            view.message = sent if isinstance(sent, discord.Message) else None
        except Exception:
            view.message = None

# ---------- setup ----------
async def setup(bot):
    cog = ExploreCog(bot)
    await bot.add_cog(cog)
    try:
        bot.tree.add_command(app_commands.Command(name="explore", description="Explora y encuentra objetos", callback=cog.explore_slash))
    except Exception:
        pass



