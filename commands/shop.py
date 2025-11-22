# commands/shop.py
import discord
from discord.ext import commands
from discord import app_commands, ui
from typing import Optional

from db import (
    get_shop, get_shop_item, add_money, add_item_to_user,
    update_rank, get_user, add_shop_item, get_inventory, create_pet, get_pet, remove_item
)

class ShopPaginationView(ui.View):
    """Vista interactiva para navegar entre páginas de la tienda"""
    def __init__(self, items: list, user_id: int, timeout: int = 300):
        super().__init__(timeout=timeout)
        self.items = items
        self.user_id = user_id
        self.current_page = 0
        self.chunk_size = 24
        self.total_pages = (len(items) + self.chunk_size - 1) // self.chunk_size
        
    def get_embed(self) -> discord.Embed:
        """Genera el embed para la página actual"""
        start_idx = self.current_page * self.chunk_size
        end_idx = start_idx + self.chunk_size
        chunk = self.items[start_idx:end_idx]
        
        rarity_colors = {
            "comun": discord.Color.from_rgb(128, 128, 128),
            "raro": discord.Color.from_rgb(0, 128, 255),
            "epico": discord.Color.from_rgb(128, 0, 255),
            "legendario": discord.Color.from_rgb(255, 215, 0),
            "maestro": discord.Color.from_rgb(255, 20, 147)
        }
        
        embed = discord.Embed(
            title=f"🏥 Farmacia Clínica de Recuperación",
            color=discord.Color.from_rgb(74, 222, 128)
        )
        embed.set_thumbnail(url="https://i.imgur.com/2yaf2wb.png")
        embed.description = f"📄 Catálogo {self.current_page + 1}/{self.total_pages}\n💊 Usa `/buy <nombre>` para adquirir medicina"
        
        rarity_emoji = {"comun": "⚪", "raro": "🔵", "epico": "🟣", "legendario": "🟠", "maestro": "🔶"}
        
        for it in chunk:
            emoji = rarity_emoji.get(it['rarity'], "❓")
            embed.add_field(
                name=f"{emoji} {it['name']}",
                value=f"💰 `{it['price']}` | {it['rarity'].upper()}\n{it['effect']}",
                inline=False
            )
        embed.set_footer(text="🏥 Tu salud mental es nuestra prioridad - Farmacia Clínica")
        return embed
    
    @ui.button(label="◀ Anterior", style=discord.ButtonStyle.blurple)
    async def anterior_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ No puedes usar esto.", ephemeral=True)
            return
        
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.send_message("Ya estás en la primera página.", ephemeral=True)
    
    @ui.button(label="Siguiente ▶", style=discord.ButtonStyle.blurple)
    async def siguiente_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ No puedes usar esto.", ephemeral=True)
            return
        
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.send_message("Ya estás en la última página.", ephemeral=True)


# ==================== AUTOCOMPLETE ====================

async def shop_items_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete para mostrar items de la tienda"""
    try:
        items = await get_shop()
        if not items:
            return []
        
        item_names = [item["name"] for item in items]
        filtered = [name for name in item_names if current.lower() in name.lower()] if current else item_names
        
        return [app_commands.Choice(name=name, value=name) for name in filtered[:25]]
    except Exception:
        return []

# ----------------- Default shop items to insert -----------------
DEFAULT_ITEMS = [
    # (name, price, type, effect, rarity)
    ("Paquete de Peluches Terapéutico", 8000, "consumible", "Recupera 50 HP mental en sesión o vende por 4000💰", "epico"),
    ("Doblador de Recuperación Económica", 900, "consumible_buff", "Dobla ganancias de terapia ocupacional 1 hora", "epico"),
    ("Danza Emocional de Paz", 3500, "consumible_buff", "Aumenta potencia psicológica +50% próximo ataque", "raro"),
    ("Poción de Furia Controlada", 2500, "consumible_damage", "Libera 60 puntos de catarsis directa", "epico"),
    ("Escudo Mental Psíquico", 1800, "consumible_shield", "Protección emocional total próximo turno", "raro"),
    ("Bastón de Poder Mental", 6500, "arma", "Potencia psicológica en confrontaciones terapéuticas", "raro"),
    ("Teléfono de Emergencia", 200, "herramienta", "Contacto en crisis emocionales agudas", "comun"),
    ("Animal de Apoyo Chihuahua", 600, "mascota", "Compañía emocional con bonificaciones pasivas", "raro"),
    ("Síndrome de Mecha Armado", 1200, "arma", "Potencia máxima en confrontaciones", "epico"),
    ("Linterna Mental", 100, "herramienta", "Revela traumas ocultos en exploración subconsciente", "comun"),
    ("Llave Maestra Psíquica", 1500, "herramienta", "Desbloquea potenciales ocultos y traumas", "epico"),
    ("Kit de Reparación Emocional", 200, "consumible", "Restaura instrumentos terapéuticos dañados", "comun"),
    ("Néctar Antiguo de Sanación", 3500, "consumible", "Restaura 100 HP mental - máxima potencia", "legendario"),
    ("Bebida de Vida Eterna", 5500, "consumible_life", "Regenera 1 vida psicológica completa", "maestro"),
    # Huevos de animales de soporte por rareza
    ("Huevo Mascota Ordinaria", 400, "huevo_mascota", "Animal de soporte común (Perro, Gato, Loro, Chihuahua)", "comun"),
    ("Huevo Mascota Especializada", 1800, "huevo_mascota", "Animal de soporte mejorado (Conejo, Hamster)", "raro"),
    ("Huevo Mascota Avanzada", 7000, "huevo_mascota", "Animal de soporte avanzado (Dragón, Fénix)", "epico"),
    ("Huevo Legendario Supremo", 35000, "huevo_mascota", "Animal legendario garantizado (Saviteto, Finopeluche, Mechones)", "legendario"),
]

# ----------------- Shop Cog -----------------
class ShopCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --------- Prefix: ver tienda ----------
    @commands.command(name="shop")
    async def shop_prefix(self, ctx):
        items = await get_shop()
        if not items:
            return await ctx.send("🏪 La farmacia clínica está cerrada por mantenimiento.")
        
        view = ShopPaginationView(items, ctx.author.id)
        embed = view.get_embed()
        embed.description = "📋 Usa `!buy Nombre exacto` para adquirir medicina.\n" + embed.description
        await ctx.send(embed=embed, view=view)

    # --------- Slash: ver tienda ----------
    @app_commands.command(name="shop", description="🏪 Farmacia Clínica - Medicinas y Recursos")
    async def shop_slash(self, interaction: discord.Interaction):
        await interaction.response.defer()
        items = await get_shop()
        if not items:
            return await interaction.followup.send("🏪 La farmacia clínica está cerrada por mantenimiento.", ephemeral=True)
        
        view = ShopPaginationView(items, interaction.user.id)
        embed = view.get_embed()
        await interaction.followup.send(embed=embed, view=view)

    # --------- Prefix: comprar ----------
    @commands.command(name="buy")
    async def buy_prefix(self, ctx, *, item_name: str):
        user = await get_user(ctx.author.id)
        item = await get_shop_item(item_name)
        if not item:
            return await ctx.send("❌ No existe ese item (usa el nombre exacto).")
        if user["dinero"] < item["price"]:
            return await ctx.send("❌ No tienes dinero suficiente.")
        
        await add_money(ctx.author.id, -item["price"])
        # add to inventory con categoría del shop (type)
        await add_item_to_user(ctx.author.id, item["name"], item["rarity"], usos=1, durabilidad=100, categoria=item["type"], poder=15)
        
        if item["type"] == "huevo_mascota":
            await ctx.send(f"🥚 ✅ Compraste **{item['name']}** por {item['price']}💰\n\n👉 Usa `/use` para eclosionar el huevo. El tiempo depende de su rareza.")
        else:
            await ctx.send(f"✅ Compraste **{item['name']}** por {item['price']}💰")

    # --------- Slash: comprar ----------
    @app_commands.command(name="buy", description="Comprar un item de la tienda")
    @app_commands.describe(item_name="Nombre del item de la tienda")
    @app_commands.autocomplete(item_name=shop_items_autocomplete)
    async def buy_slash(self, interaction: discord.Interaction, item_name: str):
        await interaction.response.defer(ephemeral=False)
        try:
            user = await get_user(interaction.user.id)
            if not user:
                return await interaction.followup.send("❌ Error: No se encontró tu perfil.", ephemeral=True)
            
            item = await get_shop_item(item_name)
            if not item:
                return await interaction.followup.send(f"❌ No existe ese item. Usa `/shop` para ver items válidos.\n💡 Buscaste: {item_name}", ephemeral=True)
            if user["dinero"] < item["price"]:
                return await interaction.followup.send(f"❌ No tienes dinero suficiente.\n💰 Necesitas: {item['price']}\n💵 Tienes: {user['dinero']}", ephemeral=True)
            
            await add_money(interaction.user.id, -item["price"])
            await add_item_to_user(interaction.user.id, item["name"], item["rarity"], usos=1, durabilidad=100, categoria=item["type"], poder=15)
            
            if item["type"] == "huevo_mascota":
                await interaction.followup.send(f"🥚 ✅ Compraste **{item['name']}** por {item['price']}💰\n\n👉 Usa `/use` para eclosionar el huevo. El tiempo depende de su rareza.")
            else:
                await interaction.followup.send(f"✅ Compraste **{item['name']}** por {item['price']}💰")
        except Exception as e:
            print(f"Error en /buy: {e}")
            await interaction.followup.send(f"❌ Error al comprar item: {str(e)}", ephemeral=True)

   

# ----------------- setup -----------------
async def setup(bot):
    cog = ShopCog(bot)
    await bot.add_cog(cog)

    # Poblado seguro de items por defecto (no duplicará, usa INSERT OR REPLACE en db.add_shop_item)
    try:
        for name, price, typ, effect, rarity in DEFAULT_ITEMS:
            await add_shop_item(name, price, typ, effect, rarity)
    except Exception:
        # si algo falla, no queremos que el bot no cargue; loguea por consola
        try:
            print("Warning: no se pudieron insertar items por defecto en la tienda (ya están o hubo un error).")
        except Exception:
            pass

    # Intentamos sincronizar comandos slash (opcional — el main ya hace sync global)
    try:
        await bot.tree.sync()
    except Exception:
        pass
