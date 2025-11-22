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
        
        # Colorear según rango
        rank_colors = {
            "Novato": discord.Color.from_rgb(128, 128, 128),
            "Enfermo Básico": discord.Color.from_rgb(0, 128, 255),
            "Enfermo Avanzado": discord.Color.from_rgb(128, 0, 255),
            "Enfermo Supremo": discord.Color.from_rgb(255, 215, 0)
        }
        color = rank_colors.get(u['rango'], discord.Color.blurple())
        
        embed = discord.Embed(
            title=f"👤 {user.name}",
            description=f"**Rango:** {u['rango']} | **Vidas:** ❤️ {u.get('vidas', 3)}",
            color=color
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        
        embed.add_field(name="💰 Dinero", value=f"```{u['dinero']:,}```", inline=True)
        embed.add_field(name="⭐ Experiencia", value=f"```{u['experiencia']:,}```", inline=True)
        embed.add_field(name="💼 Trabajo", value=f"```{u['trabajo']}```", inline=True)
        
        if inv:
            inv_text = "\n".join(f"• {i['item']} ({i['rareza']})" for i in inv[:5])
            if len(inv) > 5:
                inv_text += f"\n... y {len(inv) - 5} más"
            embed.add_field(name=f"📦 Inventario ({len(inv)}/3)", value=inv_text, inline=False)
        else:
            embed.add_field(name="📦 Inventario", value="Vacío", inline=False)
        
        embed.set_footer(text="Usa /inventario para ver todos los detalles")
        await send_fn(embed=embed)

async def setup(bot):
  await bot.add_cog(ProfileCog(bot))


    
