import discord
from discord.ext import commands
from discord import app_commands
from db import get_leaderboard, get_user

class LeaderboardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="leaderboard", description="Ver rankings de jugadores")
    @app_commands.choices(stat=[
        app_commands.Choice(name="💰 Dinero", value="dinero"),
        app_commands.Choice(name="⭐ Experiencia", value="experiencia"),
    ])
    async def leaderboard(self, interaction: discord.Interaction, stat: str = "dinero"):
        await interaction.response.defer()
        leaders = await get_leaderboard(interaction.guild_id, stat, 10)
        
        embed = discord.Embed(
            title=f"🏆 Leaderboard - {stat.capitalize()}",
            description="Top 10 jugadores",
            color=discord.Color.gold()
        )
        
        for i, leader in enumerate(leaders, 1):
            user = await self.bot.fetch_user(int(leader["user_id"])) if leader["user_id"].isdigit() else None
            name = user.name if user else f"Usuario {leader['user_id']}"
            value = leader[stat]
            embed.add_field(name=f"{i}. {name}", value=f"`{value:,}`", inline=False)
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(LeaderboardCog(bot))
