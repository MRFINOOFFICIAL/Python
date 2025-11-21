# commands/items.py
"""
Sistema de inventario e items.
Comandos: /inventario, !inventario, /use, !use
"""
import discord
from discord.ext import commands
from discord import app_commands, ui
from db import get_inventory, remove_item, add_money, update_rank
from typing import Optional


class ItemUseView(ui.View):
    """Vista interactiva para usar items"""
    def __init__(self, user_id: int, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.user_id = int(user_id)
        self.selected_item = None

    @ui.select(placeholder="Elige un item para usar", min_values=1, max_values=1)
    async def select_item(self, interaction: discord.Interaction, select: ui.Select):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ No puedes usar este selector.", ephemeral=True)
            return
        self.selected_item = int(select.values[0])
        await interaction.response.defer()
        self.stop()


class ItemsCog(commands.Cog):
    """Cog para gestionar el inventario e items"""
    def __init__(self, bot):
        self.bot = bot

    async def _inventario_send(self, user_id, send_fn):
        """Mostrar inventario completo"""
        inv = await get_inventory(user_id)
        if not inv:
            await send_fn("📦 Tu inventario está vacío.")
            return
        
        embed = discord.Embed(
            title="📦 Inventario Completo",
            description=f"Tienes {len(inv)} item(s):",
            color=discord.Color.gold()
        )
        
        for item in inv:
            embed.add_field(
                name=f"{item['item']} (ID: {item['id']})",
                value=(f"**Rareza:** {item['rareza']}\n"
                       f"**Usos:** {item['usos']}\n"
                       f"**Durabilidad:** {item['durabilidad']}%\n"
                       f"**Categoría:** {item['categoria']}"),
                inline=False
            )
        
        embed.set_footer(text="Usa /use o !use para usar un item.")
        await send_fn(embed=embed)

    async def _use_send(self, user_id, send_fn):
        """Interfaz para usar un item"""
        inv = await get_inventory(user_id)
        if not inv:
            await send_fn("❌ Tu inventario está vacío.")
            return
        
        # Crear opciones del select
        options = []
        for item in inv[:25]:  # Máximo 25 items en el select
            label = f"{item['item'][:80]}"
            value = str(item['id'])
            options.append(discord.SelectOption(label=label, value=value))
        
        if not options:
            await send_fn("❌ No hay items para usar.")
            return
        
        embed = discord.Embed(
            title="📦 Usar Item",
            description="Selecciona un item del menú desplegable:",
            color=discord.Color.blue()
        )
        
        view = ItemUseView(user_id)
        select = ui.Select(
            placeholder="Elige un item para usar",
            options=options,
            min_values=1,
            max_values=1
        )
        select.callback = view.select_item
        view.add_item(select)
        
        msg = await send_fn(embed=embed, view=view)
        await view.wait()
        
        if view.selected_item is None:
            return
        
        # Procesar el uso del item
        item_id = view.selected_item
        item = None
        for i in inv:
            if i['id'] == item_id:
                item = i
                break
        
        if not item:
            await send_fn("❌ Item no encontrado.")
            return
        
        item_name = item['item'].lower()
        
        # Efectos especiales de items
        if "kit de reparación" in item_name:
            await send_fn("🔧 **Kit de Reparación usado** — Este item repararía durabilidad (próxima versión)")
        elif "botella de sedante" in item_name:
            await send_fn("💤 **Sedante usado** — Te sientes relajado...")
        elif "teléfono" in item_name:
            await send_fn("📱 **Teléfono usado** — Llamaste a alguien... poco útil aquí")
        elif "linterna" in item_name:
            await send_fn("🔦 **Linterna encendida** — ¡Qué iluminante!")
        elif "chihuahua" in item_name:
            await send_fn("🐕 **Chihuahua activado** — Tu pequeño amiguito te acompaña")
        elif "caja de cerillas" in item_name or "cerillas" in item_name:
            await send_fn("🔥 **Cerillas encendidas** — ¡Fuego! 🔥")
        else:
            await send_fn(f"✅ **{item['item']} usado** — Efecto especial aplicado")
        
        # Remover el item
        await remove_item(item_id)

    # ==================== COMANDO INVENTARIO ====================
    
    @commands.command(name="inventario")
    async def inventario_prefix(self, ctx):
        """!inventario - Ver tu inventario completo"""
        async def send_fn(*args, **kwargs):
            return await ctx.send(*args, **kwargs)
        await self._inventario_send(ctx.author.id, send_fn)

    @app_commands.command(name="inventario", description="Ver tu inventario completo")
    async def inventario_slash(self, interaction: discord.Interaction):
        """Ver inventario completo"""
        await interaction.response.defer()
        async def send_fn(*args, **kwargs):
            return await interaction.followup.send(*args, **kwargs)
        await self._inventario_send(interaction.user.id, send_fn)

    # ==================== COMANDO USE ====================
    
    @commands.command(name="use")
    async def use_prefix(self, ctx):
        """!use - Usar un item de tu inventario"""
        async def send_fn(*args, **kwargs):
            return await ctx.send(*args, **kwargs)
        await self._use_send(ctx.author.id, send_fn)

    @app_commands.command(name="use", description="Usar un item de tu inventario")
    async def use_slash(self, interaction: discord.Interaction):
        """Usar un item del inventario"""
        await interaction.response.defer()
        async def send_fn(*args, **kwargs):
            return await interaction.followup.send(*args, **kwargs)
        await self._use_send(interaction.user.id, send_fn)


# ==================== SETUP ====================

async def setup(bot):
    """Cargar el cog de items"""
    await bot.add_cog(ItemsCog(bot))
