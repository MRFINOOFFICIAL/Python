# commands/profile.py
import discord
from discord.ext import commands
from discord import app_commands
from db import get_user, get_inventory

class ProfileCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="profile")
    async def profile_prefix(self, ctx):
        await self._profile_send(user=ctx.author, send_fn=lambda **kw: ctx.send(**kw), author_ctx=ctx)

    @app_commands.command(name="profile", description="Muestra tu perfil")
    async def profile_slash(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._profile_send(user=interaction.user, send_fn=lambda **kw: interaction.followup.send(**kw), author_ctx=interaction)

    async def _profile_send(self, user, send_fn, author_ctx):
        u = await get_user(user.id)
        inv = await get_inventory(user.id)
        embed = discord.Embed(title=f"Perfil — {user.name}", color=discord.Color.blurple())
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Dinero", value=f"{u['dinero']} 💰", inline=True)
        embed.add_field(name="Rango", value=u['rango'], inline=True)
        embed.add_field(name="Experiencia", value=f"{u['experiencia']} XP", inline=True)
        if inv:
            embed.add_field(name="Inventario (ej)", value=", ".join(i["item"] for i in inv[:6]), inline=False)
        await send_fn(embed=embed)

async def setup(bot):
  await bot.add_cog(ProfileCog(bot))


    
