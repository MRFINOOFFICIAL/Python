import discord
from discord.ext import commands
from discord import app_commands
from db import list_item_for_sale, get_market_listings, buy_from_market, get_inventory, remove_item, add_item_to_user, add_money

async def inventario_id_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete para IDs de items del inventario"""
    try:
        inv = await get_inventory(interaction.user.id)
        if not inv:
            return []
        items = [f"{item['item']} (ID: {item['id']})" for item in inv]
        filtered = [name for name in items if current.lower() in name.lower()] if current else items
        return [app_commands.Choice(name=name[:100], value=str([i['id'] for i in inv if i['item'] == name.split(' (ID:')[0]][0])) for name in filtered[:25]]
    except Exception:
        return []

class MarketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="vender-item", description="Poner item a la venta")
    @app_commands.autocomplete(item_id=inventario_id_autocomplete)
    async def sell_item(self, interaction: discord.Interaction, item_id: int, precio: int):
        await interaction.response.defer()
        
        inv = await get_inventory(interaction.user.id)
        item = next((i for i in inv if i['id'] == item_id), None)
        
        if not item:
            await interaction.followup.send("❌ Item no encontrado.")
            return
        
        await list_item_for_sale(interaction.user.id, item_id, precio)
        await interaction.followup.send(f"✅ **{item['item']}** a la venta por {precio}💰")

    @app_commands.command(name="mercado", description="Ver items en venta")
    async def market(self, interaction: discord.Interaction):
        await interaction.response.defer()
        listings = await get_market_listings(15)
        
        if not listings:
            await interaction.followup.send("📭 No hay items en el mercado.")
            return
        
        embed = discord.Embed(title="🏪 Mercado", color=discord.Color.purple())
        for listing in listings:
            try:
                user = await self.bot.fetch_user(int(listing['vendedor']))
                embed.add_field(
                    name=f"ID: {listing['id']} - {user.name}",
                    value=f"Item #{listing['item_id']}: {listing['precio']}💰",
                    inline=False
                )
            except:
                pass
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(MarketCog(bot))
