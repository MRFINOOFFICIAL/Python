# commands/explore.py
"""
Sistema de exploración para encontrar objetos y cofres.
Conectado con rob.py para compartir ITEM_STATS.
"""
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View
from db import add_item_to_user, get_inventory, remove_item, get_lives, set_lives, reset_user_progress, update_mission_progress, add_pet_xp
import random
from typing import Tuple, List, Optional
from cache import set_buff, get_buff, clear_buff


# ==================== DATOS DE EXPLORACIÓN ====================

LOOT_TABLE: List[Tuple[str, str, int]] = [
    # Items básicos
    ("Cinta adhesiva", "comun", 1),
    ("Botella de sedante", "comun", 1),
    ("Cuchillo oxidado", "raro", 3),
    ("Pistola vieja", "raro", 5),  # Cambio: era épico, ahora raro
    ("Botiquín", "comun", 1),
    ("Arma blanca artesanal", "raro", 3),
    ("Palo golpeador de parejas felices", "raro", 5),  # Cambio: era épico, ahora raro
    ("Savi peluche", "raro", 5),  # Cambio: era épico, ahora raro
    ("Hélice de ventilador", "comun", 1),
    ("Aconsejante Fantasma", "raro", 5),  # Cambio: era épico, ahora raro
    ("ID falso", "raro", 3),
    ("Máscara de Xfi", "raro", 5),  # Cambio: era épico, ahora raro
    # Items especiales
    ("Bastón de Staff", "raro", 4),
    ("Teléfono", "comun", 1),
    ("Chihuahua", "raro", 2),
    ("Mecha Enojado", "legendario", 1),  # Cambio: ahora solo se obtiene derrotando al boss
    ("Linterna", "comun", 1),
    ("Llave Maestra", "legendario", 1),  # Cambio: ahora raro de encontrar
    # Armas especiales de bosses (muy raras)
    ("Espada del Goblin", "legendario", 1),
    ("Hacha del Orco", "legendario", 1),
    ("Vara de la Bruja", "legendario", 1),
    ("Núcleo de Savi", "legendario", 1),
    ("Aliento del Dragón", "maestro", 1),
    ("Corona del Rey Esqueleto", "maestro", 1),
    ("Espada Oscura", "maestro", 1),
    ("Esencia de Savi", "maestro", 1),
    ("Cordura Rota", "maestro", 1),
    ("Bisturí Misterioso", "maestro", 1),
    ("Jeringa de Hierro", "maestro", 1),
    ("Cetro del Caos", "maestro", 1),
    ("Espada de Fino", "maestro", 1),
    # Extras para variedad
    ("Anillo oxidado", "comun", 1),
    ("Mapa antiguo", "raro", 1),
    ("Gafas de soldador", "raro", 1),
    ("Caja de cerillas", "comun", 1),
    ("Receta secreta", "raro", 1),  # Cambio: era épico, ahora raro
    ("Núcleo energético", "legendario", 1),
    ("Fragmento Omega", "maestro", 1),
    ("Traje ritual", "legendario", 1),
    ("Placa de identificación", "raro", 1),
    ("Cable USB", "comun", 1),
    ("Garrafa de aceite", "comun", 1),
    ("Guitarra rota", "raro", 1),
]

WEIGHTS = [
    40, 40, 10, 3, 30, 15, 3, 3, 25, 3, 10, 3,
    8, 30, 15, 1, 20, 1,
    # Armas de bosses (muy bajos pesos, rarísimas)
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    # Resto
    35, 12, 10, 40, 8, 1, 1, 2, 10, 50, 35, 18
]
assert len(WEIGHTS) == len(LOOT_TABLE), "Pesos no coinciden con tabla de loot"

# Configuración de cofres
CHEST_CHANCE = 0.16  # Aumentado de 0.12 a 0.16 (16% de probabilidad de cofre)
CHEST_RARITY_WEIGHTS = {"comun": 60, "raro": 30, "epico": 5, "legendario": 4, "maestro": 1}  # Reducido épico de 10 a 5
CHEST_YIELD = {"comun": (1, 1), "raro": (1, 2), "epico": (1, 2), "legendario": (2, 3), "maestro": (2, 4)}
SEALED_PROB = {"epico": 0.03, "legendario": 0.15, "maestro": 0.65}
CONSUME_KEY_ON_SEALED = True

# Emojis por rareza
RARITY_EMOJI = {"comun": "⚪", "raro": "🔵", "epico": "🟣", "legendario": "🟠", "maestro": "🔶"}

# Stats de items (sincronizado con rob.py)
ITEM_STATS = {
    "cinta adhesiva": {"categoria": "herramientas", "poder": 3},
    "botella de sedante": {"categoria": "quimicos", "poder": 6},
    "cuchillo oxidado": {"categoria": "arma", "poder": 18},
    "pistola vieja": {"categoria": "arma", "poder": 35},
    "botiquín": {"categoria": "salud", "poder": 2},
    "arma blanca artesanal": {"categoria": "arma", "poder": 25},
    "palo golpeador de parejas felices": {"categoria": "arma", "poder": 30},
    "savi peluche": {"categoria": "engano", "poder": 10},
    "hélice de ventilador": {"categoria": "herramientas", "poder": 8},
    "aconsejante fantasma": {"categoria": "engano", "poder": 30},
    "id falso": {"categoria": "engano", "poder": 22},
    "máscara de xfi": {"categoria": "engano", "poder": 35},
    "bastón de staff": {"categoria": "herramientas", "poder": 28},
    "teléfono": {"categoria": "tecnologia", "poder": 12},
    "chihuahua": {"categoria": "mascota", "poder": 5},
    "mecha enojado": {"categoria": "arma", "poder": 40},
    "linterna": {"categoria": "herramientas", "poder": 7},
    "llave maestra": {"categoria": "herramientas", "poder": 40},
    "anillo oxidado": {"categoria": "accesorio", "poder": 4},
    "mapa antiguo": {"categoria": "herramientas", "poder": 6},
    "gafas de soldador": {"categoria": "accesorio", "poder": 8},
    "caja de cerillas": {"categoria": "herramientas", "poder": 5},
    "receta secreta": {"categoria": "quimicos", "poder": 16},
    "núcleo energético": {"categoria": "tecnologia", "poder": 45},
    "fragmento omega": {"categoria": "arma", "poder": 50},
    "traje ritual": {"categoria": "ropa", "poder": 35},
    "placa de identificación": {"categoria": "accesorio", "poder": 7},
    "cable usb": {"categoria": "tecnologia", "poder": 9},
    "garrafa de aceite": {"categoria": "quimicos", "poder": 10},
    "guitarra rota": {"categoria": "arma", "poder": 20},  # Raro, debe tener más poder
    # Armas especiales de bosses
    "espada del goblin": {"categoria": "arma", "poder": 42},
    "hacha del orco": {"categoria": "arma", "poder": 44},
    "vara de la bruja": {"categoria": "arma", "poder": 46},
    "núcleo de savi": {"categoria": "arma", "poder": 48},
    "aliento del dragón": {"categoria": "arma", "poder": 55},
    "corona del rey esqueleto": {"categoria": "arma", "poder": 54},
    "espada oscura": {"categoria": "arma", "poder": 56},
    "esencia de savi": {"categoria": "arma", "poder": 58},
    "cordura rota": {"categoria": "arma", "poder": 60},
    "bisturí misterioso": {"categoria": "arma", "poder": 61},
    "jeringa de hierro": {"categoria": "arma", "poder": 62},
    "cetro del caos": {"categoria": "arma", "poder": 63},
    "espada de fino": {"categoria": "arma", "poder": 65},
}


# ==================== FUNCIONES AUXILIARES ====================

def pick_chest_rarity() -> str:
    """Selecciona rareza de cofre aleatoria"""
    keys = list(CHEST_RARITY_WEIGHTS.keys())
    weights = list(CHEST_RARITY_WEIGHTS.values())
    return random.choices(keys, weights=weights, k=1)[0]


def pick_loot_from_rarity(rarity: str, n: int) -> List[Tuple[str, str, int]]:
    """Obtiene n items de una rareza específica"""
    pool = [x for x in LOOT_TABLE if x[1].lower() == rarity.lower()]
    if not pool:
        if rarity == "maestro":
            pool = [x for x in LOOT_TABLE if x[1].lower() in ("maestro", "legendario", "epico")]
        elif rarity == "legendario":
            pool = [x for x in LOOT_TABLE if x[1].lower() in ("legendario", "epico", "raro")]
    if not pool:
        pool = LOOT_TABLE.copy()
    return [random.choice(pool) for _ in range(n)]


def has_item_in_inv(inv: list, name_substr: str) -> bool:
    """Verifica si el usuario tiene un item en el inventario"""
    ns = name_substr.lower()
    return any(ns == i["item"].lower() for i in inv)


def find_item_id_by_name(inv: list, name_substr: str) -> Optional[int]:
    """Encuentra el ID de un item por nombre"""
    ns = name_substr.lower()
    for i in inv:
        if ns == i["item"].lower():
            return i["id"]
    return None


# ==================== VISTAS (DISCORD UI) ====================

class ReplaceView(View):
    """Vista para reemplazar items cuando el inventario está lleno"""
    
    def __init__(self, user_id: int, new_item: Tuple[str, str, int], timeout: int = 60):
        super().__init__(timeout=timeout)
        self.user_id = int(user_id)
        self.new_item = new_item
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    async def on_timeout(self) -> None:
        """Desactiva botones cuando expira el timeout"""
        try:
            for child in self.children:
                if hasattr(child, 'disabled'):
                    setattr(child, 'disabled', True)
        except Exception:
            pass
        if self.message:
            try:
                await self.message.edit(content="⌛ Tiempo terminado, botones desactivados.", view=self)
            except Exception:
                pass


class ChestOpenView(View):
    """Vista para abrir o ignorar cofres"""
    
    def __init__(self, user_id: int, chest_rarity: str, yielding: Tuple[int, int], sealed: bool = False, timeout: int = 30):
        super().__init__(timeout=timeout)
        self.user_id = int(user_id)
        self.chest_rarity = chest_rarity
        self.yielding = yielding
        self.message: Optional[discord.Message] = None
        self.opened: Optional[bool] = None
        self.sealed = sealed

        btn_open = Button(label="Abrir cofre", style=discord.ButtonStyle.success)
        btn_ignore = Button(label="Ignorar", style=discord.ButtonStyle.secondary)

        async def open_cb(inter: discord.Interaction):
            if inter.user.id != self.user_id:
                await inter.response.send_message("❌ Solo quien encontró el cofre puede abrirlo.", ephemeral=True)
                return
            self.opened = True
            await inter.response.defer()
            self.stop()

        async def ignore_cb(inter: discord.Interaction):
            if inter.user.id != self.user_id:
                await inter.response.send_message("❌ Solo quien encontró el cofre puede ignorarlo.", ephemeral=True)
                return
            self.opened = False
            await inter.response.edit_message(content="Has decidido ignorar el cofre.", view=None)
            self.stop()

        btn_open.callback = open_cb
        btn_ignore.callback = ignore_cb
        self.add_item(btn_open)
        self.add_item(btn_ignore)

    async def on_timeout(self) -> None:
        """Desactiva botones cuando expira el timeout"""
        try:
            for child in self.children:
                if hasattr(child, 'disabled'):
                    setattr(child, 'disabled', True)
        except Exception:
            pass
        if self.message:
            try:
                await self.message.edit(content="⌛ Tiempo terminado. Cofre perdido.", view=self)
            except Exception:
                pass


# ==================== COG PRINCIPAL ====================

class ExploreCog(commands.Cog):
    """Sistema de exploración"""
    
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="explore")
    @commands.cooldown(1, 25, commands.BucketType.user)
    async def explore_prefix(self, ctx):
        """Comando prefix: explorar"""
        await self._do_explore(ctx.author, send_fn=lambda **kw: ctx.send(**kw), author_ctx=ctx)

    @app_commands.command(name="explore", description="🌲 Explora y encuentra objetos y cofres")
    async def explore_slash(self, interaction: discord.Interaction):
        """Comando slash: explorar"""
        await interaction.response.defer()
        await self._do_explore(interaction.user, send_fn=lambda **kw: interaction.followup.send(**kw), author_ctx=interaction)

    async def _do_explore(self, user, send_fn, author_ctx):
        """Lógica principal de exploración"""
        inv = await get_inventory(user.id)
        has_linterna = has_item_in_inv(inv, "linterna")

        # Decidir entre cofre e item
        chest_chance = CHEST_CHANCE + (0.05 if has_linterna else 0.0)
        
        if random.random() < chest_chance:
            await self._handle_chest(user, send_fn, has_linterna)
        else:
            await self._handle_item(user, send_fn, inv)

    async def _handle_chest(self, user, send_fn, has_linterna: bool):
        """Maneja el encuentro de un cofre"""
        chest_rarity = pick_chest_rarity()
        sealed = random.random() < SEALED_PROB.get(chest_rarity, 0)

        yield_min, yield_max = CHEST_YIELD.get(chest_rarity, (1, 1))
        
        embed = discord.Embed(
            title=f"{RARITY_EMOJI.get(chest_rarity, '🎁')} ¡Has encontrado un cofre {chest_rarity.capitalize()}!",
            description=f"{user.mention}, encontraste un **cofre {chest_rarity.capitalize()}**.\n\n"
                        f"{'🔐 Está sellado (requiere Llave Maestra).' if sealed else 'Pulsa Abrir cofre para abrirlo (tiempo limitado).'}",
            color=discord.Color.gold() if chest_rarity in ("epico", "legendario", "maestro") else discord.Color.blurple()
        )
        
        view = ChestOpenView(user.id, chest_rarity, (yield_min, yield_max), sealed=sealed, timeout=30)
        sent = await send_fn(embed=embed, view=view)
        view.message = sent if isinstance(sent, discord.Message) else None

        await view.wait()

        if view.opened is None or not view.opened:
            return

        # Verificar Llave Maestra si el cofre está sellado
        inv_now = await get_inventory(user.id)
        key_id = find_item_id_by_name(inv_now, "llave maestra")
        
        if sealed and not key_id:
            await (view.message.edit(content="🔒 El cofre estaba sellado y no tienes Llave Maestra.", view=None) 
                   if view.message else send_fn(content="🔒 El cofre estaba sellado y no tienes Llave Maestra."))
            return
        
        if sealed and key_id and CONSUME_KEY_ON_SEALED:
            await remove_item(key_id)

        # Animación de apertura
        try:
            if view.message:
                for i, chars in enumerate(["░░░", "▓░░", "▓▓░", "▓▓▓"]):
                    await view.message.edit(content=f"Abriendo cofre... {chars}", embed=None, view=None)
                    if i < 3:
                        await asyncio.sleep(0.7)
        except Exception:
            pass

        # Generar y agregar loot
        n = random.randint(yield_min, yield_max)
        if has_linterna and chest_rarity in ("raro", "epico", "legendario"):
            n = min(n + 1, CHEST_YIELD.get(chest_rarity, (1, 4))[1])

        picks = pick_loot_from_rarity(chest_rarity, n)
        added_names = []
        
        for name, rarity, usos in picks:
            key = name.lower()
            stats = ITEM_STATS.get(key, {})
            categoria = stats.get("categoria", "desconocido")
            poder = stats.get("poder", 0)
            await add_item_to_user(user.id, name, rarity, usos=usos, durabilidad=100, categoria=categoria, poder=poder)
            await add_pet_xp(user.id, 10)
            added_names.append(f"{name} ({rarity})")

            # Efectos especiales
            if key == "telefono":
                set_buff(user.id, "telefono_extra_time", 6)
            elif key == "chihuahua":
                await add_item_to_user(user.id, "Moneda de compañía", "comun", usos=1, durabilidad=100, categoria="consumible", poder=0)

        result_text = "✅ Has abierto el cofre y obtuviste:\n" + "\n".join(f"- {x}" for x in added_names)
        try:
            if view.message:
                await view.message.edit(content=result_text, embed=None, view=None)
            else:
                await send_fn(content=result_text)
        except Exception:
            await send_fn(content=result_text)

    async def _handle_item(self, user, send_fn, inv: list):
        """Maneja el encuentro de un item normal"""
        # 20% probabilidad de morir en explore
        if random.random() < 0.20:
            lives = await get_lives(user.id)
            if lives > 1:
                await set_lives(user.id, lives - 1)
                await send_fn(content=f"💀 ¡Encontraste un peligro! Perdiste una vida. Te quedan: **{lives - 1}** vidas.")
            else:
                await reset_user_progress(user.id)
                await send_fn(content=f"💀 ¡HAS MUERTO EN LA EXPLORACIÓN! 💀\n\n😢 Perdiste TODO tu progreso:\n- Dinero: **0💰**\n- Experiencia: **0xp**\n- Inventario: **vacío**\n- Vidas: **3** (reseteadas)\n\n📖 Compra **Bebida de la Vida** (8000💰) en la tienda para obtener más vidas y no perderlo todo.")
            return
        
        item = random.choices(LOOT_TABLE, weights=WEIGHTS, k=1)[0]
        name, rarity, usos = item
        
        key = name.lower()
        stats = ITEM_STATS.get(key, {})
        categoria = stats.get("categoria", "desconocido")
        poder = stats.get("poder", 0)

        # Si hay espacio en el inventario
        if len(inv) < 3:
            await add_item_to_user(user.id, name, rarity, usos=usos, durabilidad=100, categoria=categoria, poder=poder)
            await add_pet_xp(user.id, 10)
            # Actualizar progreso de misión "explorar"
            await update_mission_progress(user.id)
            
            embed = discord.Embed(
                title=f"{RARITY_EMOJI.get(rarity, '')} 🌲 Exploración",
                description=f"{user.mention} encontraste **{name}** ({rarity})!",
                color=discord.Color.teal()
            )
            embed.set_footer(text="Sigue explorando para encontrar objetos raros y cofres.")
            
            # Efectos especiales
            if key == "linterna":
                set_buff(user.id, "linterna_boost_until", asyncio.get_event_loop().time() + 3600 * 24)
                embed.add_field(name="Uso especial", value="🪄 La Linterna aumenta tus probabilidades de cofres/objetos raros durante 24h.", inline=False)
            elif key == "telefono":
                set_buff(user.id, "telefono_extra_time", 6)
                embed.add_field(name="Uso especial", value="📱 Teléfono: +6s en la próxima pregunta de trabajo.", inline=False)
            elif key == "chihuahua":
                embed.add_field(name="Mascota", value="🐶 Chihuahua: te acompaña y te dio una moneda de compañía.", inline=False)
            
            await send_fn(embed=embed)
            return

        # Inventario lleno - ofrecer reemplazar
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
                    await interaction.response.send_message("❌ Solo quien encontró el objeto puede reemplazar.", ephemeral=True)
                    return
                await remove_item(item_id)
                await add_item_to_user(interaction.user.id, name, rarity, usos=usos, durabilidad=100, categoria=categoria, poder=poder)
                await add_pet_xp(interaction.user.id, 10)
                await interaction.response.edit_message(content=f"✅ Reemplazaste **{item_name}** con **{name}**!", embed=None, view=None)
            
            btn.callback = cb
            view.add_item(btn)

        sent = await send_fn(embed=embed, view=view)
        view.message = sent if isinstance(sent, discord.Message) else None


# ==================== SETUP ====================

async def setup(bot):
    """Carga el cog al bot"""
    await bot.add_cog(ExploreCog(bot))
