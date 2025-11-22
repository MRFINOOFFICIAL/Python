# commands/shop.py
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from db import (
    get_shop, get_shop_item, add_money, add_item_to_user,
    update_rank, get_user, add_shop_item, get_inventory
)


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
    ("Paquete de peluches fino", 10000, "consumible", "Recupera 50 HP en combate o vende por 5000💰", "epico"),
    ("x2 de dinero de mecha", 1200, "consumible_buff", "Duplica dinero ganado en el trabajo durante 1 hora", "epico"),
    ("Danza de Saviteto", 5000, "consumible_buff", "Aumenta tu daño en 50% en el próximo ataque", "raro"),
    ("Poción de Furia", 3500, "consumible_damage", "Inflige 60 de daño directo al jefe", "epico"),
    ("Escudo Mágico", 2800, "consumible_shield", "Te protege del próximo ataque enemigo", "raro"),
    # 7 adicionales solicitadas
    ("Bastón de Staff", 9500, "arma", "Aumenta el poder en robos y minijuegos relacionados.", "raro"),
    ("Teléfono", 300, "herramienta", "Útil para minijuegos y algunas interacciones.", "comun"),
    ("Chihuahua", 900, "mascota", "Mascota que puede ofrecer pequeñas bonificaciones pasivas.", "raro"),
    ("Mecha Enojado", 1800, "arma", "Arma poderosa con alto poder en robos.", "epico"),
    ("Linterna", 150, "herramienta", "Permite encontrar objetos más raros al explorar.", "comun"),
    ("Llave Maestra", 2200, "herramienta", "Aumenta posibilidades de saqueo exitoso y desbloquea cofres.", "epico"),
    ("Kit de reparación", 250, "consumible", "Restaura durabilidad de un item del inventario.", "comun"),
    ("Nektar Antiguo", 4200, "consumible", "Recupera 100 HP en combate - poder completo", "legendario"),
    ("Bebida de la Vida", 8000, "consumible_life", "Te da una vida extra. Úsala con /use", "maestro"),
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
        embed = discord.Embed(title="🏪 Tienda — Los Ezquisos", color=discord.Color.green())
        embed.set_thumbnail(url="https://i.imgur.com/2yaf2wb.png")
        embed.description = "Usa `!buy Nombre exacto` para comprar. También disponibles como `/buy`."
        for it in items:
            # mostrar name — price — rarity y la descripción/effect
            embed.add_field(
                name=f"{it['name']} — {it['price']}💰 ({it['rarity']})",
                value=f"**Tipo:** {it['type']} — **Descripción:** {it['effect']}",
                inline=False
            )
        await ctx.send(embed=embed)

    # --------- Slash: ver tienda ----------
    @app_commands.command(name="shop", description="Ver la tienda")
    async def shop_slash(self, interaction: discord.Interaction):
        await interaction.response.defer()
        items = await get_shop()
        if not items:
            return await interaction.followup.send("La tienda está vacía por ahora.", ephemeral=True)
        embed = discord.Embed(title="🏪 Tienda — Los Ezquisos", color=discord.Color.green())
        embed.set_thumbnail(url="https://i.imgur.com/2yaf2wb.png")
        embed.description = "Usa `/buy item_name` para comprar."
        for it in items:
            embed.add_field(
                name=f"{it['name']} — {it['price']}💰 ({it['rarity']})",
                value=f"**Tipo:** {it['type']} — **Descripción:** {it['effect']}",
                inline=False
            )
        await interaction.followup.send(embed=embed)

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
        await ctx.send(f"✅ Compraste **{item['name']}** por {item['price']}💰")

    # --------- Slash: comprar ----------
    @app_commands.command(name="buy", description="Comprar un item de la tienda")
    @app_commands.describe(item_name="Nombre del item de la tienda")
    @app_commands.autocomplete(item_name=shop_items_autocomplete)
    async def buy_slash(self, interaction: discord.Interaction, item_name: str):
        await interaction.response.defer(ephemeral=False)
        user = await get_user(interaction.user.id)
        item = await get_shop_item(item_name)
        if not item:
            return await interaction.followup.send("❌ No existe ese item (usa el nombre exacto).", ephemeral=True)
        if user["dinero"] < item["price"]:
            return await interaction.followup.send("❌ No tienes dinero suficiente.", ephemeral=True)
        await add_money(interaction.user.id, -item["price"])
        # add to inventory con categoría del shop (type)
        await add_item_to_user(interaction.user.id, item["name"], item["rarity"], usos=1, durabilidad=100, categoria=item["type"], poder=15)
        await interaction.followup.send(f"✅ Compraste **{item['name']}** por {item['price']}💰")

   

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
