import discord
from discord.ext import commands
from discord import app_commands
from db import (create_trade, get_pending_trades, accept_trade, 
                get_inventory, remove_item, add_item_to_user)

class TradingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ofrecer-trade", description="Ofrecer intercambio con otro jugador")
    async def offer_trade(self, interaction: discord.Interaction, usuario: discord.User, item_tuyo: str, item_suyo: str):
        await interaction.response.defer()
        
        inv_yo = await get_inventory(interaction.user.id)
        inv_otro = await get_inventory(usuario.id)
        
        mi_item = next((i for i in inv_yo if i['item'].lower() == item_tuyo.lower()), None)
        su_item = next((i for i in inv_otro if i['item'].lower() == item_suyo.lower()), None)
        
        if not mi_item or not su_item:
            await interaction.followup.send("❌ Item no encontrado en alguno de los inventarios.")
            return
        
        await create_trade(interaction.user.id, usuario.id, mi_item['id'], su_item['id'])
        await interaction.followup.send(f"✅ Oferta enviada a {usuario.mention}: Tu **{item_tuyo}** por su **{item_suyo}**")

    @app_commands.command(name="mis-trades", description="Ver trades pendientes")
    async def my_trades(self, interaction: discord.Interaction):
        await interaction.response.defer()
        trades = await get_pending_trades(interaction.user.id)
        
        if not trades:
            await interaction.followup.send("No tienes trades pendientes.")
            return
        
        embed = discord.Embed(title="📦 Trades Pendientes", color=discord.Color.blue())
        for trade in trades:
            try:
                user = await self.bot.fetch_user(int(trade['remitente']))
                embed.add_field(
                    name=f"ID: {trade['id']} - {user.name}",
                    value=f"Te ofrece item #{trade['item_remitente']} por tu item #{trade['item_receptor']}",
                    inline=False
                )
            except:
                pass
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(TradingCog(bot))
