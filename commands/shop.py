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
            title=f"🏪 Tienda — Los Ezquisos",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url="https://i.imgur.com/2yaf2wb.png")
        embed.description = f"📄 Página {self.current_page + 1}/{self.total_pages}\n💡 Usa `/buy <nombre>` para comprar"
        
        rarity_emoji = {"comun": "⚪", "raro": "🔵", "epico": "🟣", "legendario": "🟠", "maestro": "🔶"}
        
        for it in chunk:
            emoji = rarity_emoji.get(it['rarity'], "❓")
            embed.add_field(
                name=f"{emoji} {it['name']}",
                value=f"💰 `{it['price']}` | {it['rarity'].upper()}\n{it['effect']}",
                inline=False
            )
        embed.set_footer(text="¡Mejora tu arsenal en la tienda!")
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
    ("Paquete de peluches fino", 8000, "consumible", "Recupera 50 HP en combate o vende por 4000💰", "epico"),
    ("x2 de dinero de mecha", 900, "consumible_buff", "Duplica dinero ganado en el trabajo durante 1 hora", "epico"),
    ("Danza de Saviteto", 3500, "consumible_buff", "Aumenta tu daño en 50% en el próximo ataque", "raro"),
    ("Poción de Furia", 2500, "consumible_damage", "Inflige 60 de daño directo al jefe", "epico"),
    ("Escudo Mágico", 1800, "consumible_shield", "Te protege del próximo ataque enemigo", "raro"),
    # 7 adicionales solicitadas
    ("Bastón de Staff", 6500, "arma", "Aumenta el poder en robos y minijuegos relacionados.", "raro"),
    ("Teléfono", 200, "herramienta", "Útil para minijuegos y algunas interacciones.", "comun"),
    ("Chihuahua", 600, "mascota", "Mascota que puede ofrecer pequeñas bonificaciones pasivas.", "raro"),
    ("Mecha Enojado", 1200, "arma", "Arma poderosa con alto poder en robos.", "epico"),
    ("Linterna", 100, "herramienta", "Permite encontrar objetos más raros al explorar.", "comun"),
    ("Llave Maestra", 1500, "herramienta", "Aumenta posibilidades de saqueo exitoso y desbloquea cofres.", "epico"),
    ("Kit de reparación", 200, "consumible", "Restaura durabilidad de un item del inventario.", "comun"),
    ("Nektar Antiguo", 3500, "consumible", "Recupera 100 HP en combate - poder completo", "legendario"),
    ("Bebida de la Vida", 5500, "consumible_life", "Te da una vida extra. Úsala con /use", "maestro"),
    # Huevos de mascotas por rareza - más accesibles
    ("Huevo Común", 400, "huevo_mascota", "Alta probabilidad de mascota común (Chihuahua, Gato, Perro, Loro)", "comun"),
    ("Huevo Raro", 1800, "huevo_mascota", "Probabilidad aumentada de mascota rara (Conejo, Hamster)", "raro"),
    ("Huevo Épico", 7000, "huevo_mascota", "Probabilidad aumentada de mascota épica (Dragón, Fenix)", "epico"),
    ("Huevo Legendario", 35000, "huevo_mascota", "Máxima probabilidad de mascota legendaria (Saviteto, Finopeluche, Mechones)", "legendario"),
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
            return await ctx.send("La tienda está vacía por ahora.")
        
        view = ShopPaginationView(items, ctx.author.id)
        embed = view.get_embed()
        embed.description = "Usa `!buy Nombre exacto` para comprar.\n" + embed.description
        await ctx.send(embed=embed, view=view)

    # --------- Slash: ver tienda ----------
    @app_commands.command(name="shop", description="Ver la tienda")
    async def shop_slash(self, interaction: discord.Interaction):
        await interaction.response.defer()
        items = await get_shop()
        if not items:
            return await interaction.followup.send("La tienda está vacía por ahora.", ephemeral=True)
        
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
