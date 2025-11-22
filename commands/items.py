# commands/items.py
"""
Sistema de inventario e items.
Comandos: /inventario, !inventario, /use, !use
"""
import discord
from discord.ext import commands
from discord import app_commands, ui
from db import get_inventory, remove_item, add_money, update_rank, repair_item, add_lives, create_pet, get_pet
from typing import Optional


# ==================== AUTOCOMPLETE ====================

async def inventario_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete para mostrar items del inventario"""
    try:
        inv = await get_inventory(interaction.user.id)
        if not inv:
            return []
        
        items = [item["item"] for item in inv]
        filtered = [name for name in items if current.lower() in name.lower()] if current else items
        
        return [app_commands.Choice(name=name[:100], value=name) for name in filtered[:25]]
    except Exception:
        return []


async def use_item_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete para usar items"""
    try:
        inv = await get_inventory(interaction.user.id)
        if not inv:
            return []
        
        items = [f"{item['item']} (ID: {item['id']})" for item in inv]
        filtered = [name for name in items if current.lower() in name.lower()] if current else items
        
        return [app_commands.Choice(name=name[:100], value=name.split("(ID: ")[1].rstrip(")")) for name in filtered[:25]]
    except Exception:
        return []


async def repair_item_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete para reparar items (solo items con durabilidad < 100)"""
    try:
        inv = await get_inventory(interaction.user.id)
        if not inv:
            return []
        
        # Solo mostrar items dañados
        damaged = [item for item in inv if item['durabilidad'] < 100]
        if not damaged:
            return []
        
        items = [f"{item['item']} ({item['durabilidad']}%)" for item in damaged]
        filtered = [name for name in items if current.lower() in name.lower()] if current else items
        
        # Retornar ID del item
        return [app_commands.Choice(name=name[:100], value=str([d['id'] for d in damaged if str(d['id']) in name or d['item'] in name][0])) for name in filtered[:25] if any([d['id'] for d in damaged if str(d['id']) in name or d['item'] in name])]
    except Exception:
        return []


class ItemUseView(ui.View):
    """Vista interactiva para usar items"""
    def __init__(self, user_id: int, options: list = None, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.user_id = int(user_id)
        self.selected_item = None
        
        # Agregar select con opciones dinámicas si se proporcionan
        if options:
            select = ui.Select(
                placeholder="Elige un item para usar",
                options=options,
                min_values=1,
                max_values=1
            )
            async def select_callback(interaction: discord.Interaction):
                await self.select_item(interaction, select)
            select.callback = select_callback
            self.add_item(select)

    async def select_item(self, interaction: discord.Interaction, select: ui.Select = None):
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
        
        # Pasar opciones al constructor de ItemUseView
        view = ItemUseView(user_id, options=options)
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
        
        # Efectos especiales de HUEVOS DE MASCOTAS
        if "huevo de" in item_name:
            import asyncio
            existing_pet = await get_pet(user_id)
            if existing_pet:
                await send_fn("❌ Ya tienes una mascota. Usa `/cambiar-mascota` para cambiarla.")
                return
            
            # Extraer nombre y rareza
            pet_name = item_name.replace("huevo de ", "").strip()
            rareza = item['rareza']
            
            # Tiempos de eclosión según rareza
            times = {
                "comun": (3, "⏳ El huevo brilla suavemente..."),
                "raro": (6, "✨ El huevo empieza a brillar más intensamente..."),
                "epico": (10, "🌟 El huevo está RADIANTE..."),
                "legendario": (15, "⚡ El huevo EXPLOTA en energía pura...")
            }
            
            duration, msg = times.get(rareza, (5, "⏳ El huevo se está abriendo..."))
            
            # Animación de eclosión
            await send_fn(f"🥚 {msg}")
            await asyncio.sleep(duration)
            
            # Crear mascota
            rareza_map = {"comun": "común", "raro": "raro", "epico": "épico", "legendario": "legendario"}
            await create_pet(user_id, pet_name, rareza_map.get(rareza, "común"))
            
            # Remover el huevo
            await remove_item(item['id'])
            
            await send_fn(f"🐾 ¡¡¡HA ECLOSIONADO !!! 🐾\n✨ ¡Tu **{pet_name.capitalize()}** ha nacido! ✨\n\nUsa `/mi-mascota` para verlo en acción.")
            return
        
        # Efectos especiales de items
        if "bebida de la vida" in item_name:
            await add_lives(user_id, 1)
            await send_fn("🍷 **Bebida de la Vida usado** — ¡Has ganado una vida extra! 💚")
        elif "kit de reparación" in item_name:
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
    @app_commands.autocomplete(item_name=use_item_autocomplete)
    async def use_slash(self, interaction: discord.Interaction, item_name: Optional[str] = None):
        """Usar un item del inventario"""
        await interaction.response.defer()
        async def send_fn(*args, **kwargs):
            return await interaction.followup.send(*args, **kwargs)
        await self._use_send(interaction.user.id, send_fn)

    # ==================== COMANDO REPAIR ====================
    
    async def _repair_send(self, user_id, send_fn):
        """Interfaz para reparar un item"""
        inv = await get_inventory(user_id)
        
        # Filtrar items con durabilidad menor a 100
        damaged = [item for item in inv if item['durabilidad'] < 100]
        
        if not damaged:
            await send_fn("✅ Todos tus items tienen durabilidad completa.")
            return
        
        # Verificar si tiene Kit de reparación
        has_kit = any(item['item'].lower() == "kit de reparación" for item in inv)
        
        if not has_kit:
            await send_fn("❌ No tienes un Kit de reparación. Compra uno en la tienda.")
            return
        
        # Crear opciones para seleccionar item dañado
        options = []
        for item in damaged[:25]:
            label = f"{item['item']} ({item['durabilidad']}%)"
            value = str(item['id'])
            options.append(discord.SelectOption(label=label, value=value))
        
        embed = discord.Embed(
            title="🔧 Reparar Item",
            description="Selecciona un item dañado para reparar:",
            color=discord.Color.gold()
        )
        
        view = ItemUseView(user_id)
        select = ui.Select(
            placeholder="Elige un item para reparar",
            options=options,
            min_values=1,
            max_values=1
        )
        async def select_callback(interaction: discord.Interaction):
            await view.select_item(interaction, select)
        select.callback = select_callback
        view.add_item(select)
        
        msg = await send_fn(embed=embed, view=view)
        await view.wait()
        
        if view.selected_item is None:
            return
        
        # Reparar el item
        item_id = view.selected_item
        damaged_item = next((i for i in damaged if i['id'] == item_id), None)
        
        if not damaged_item:
            await send_fn("❌ Item no encontrado.")
            return
        
        # Restaurar durabilidad a 100
        await repair_item(item_id, 100)
        
        # Eliminar Kit de reparación
        kit = next((i for i in inv if i['item'].lower() == "kit de reparación"), None)
        if kit:
            await remove_item(kit['id'])
        
        embed = discord.Embed(
            title="✅ Item Reparado",
            description=f"**{damaged_item['item']}** ha sido reparado a 100% de durabilidad.",
            color=discord.Color.green()
        )
        embed.add_field(name="Kit usado", value="Se consumió 1 Kit de reparación", inline=False)
        
        await send_fn(embed=embed)

    @commands.command(name="repair")
    async def repair_prefix(self, ctx):
        """!repair - Reparar un item dañado con Kit de reparación"""
        async def send_fn(*args, **kwargs):
            return await ctx.send(*args, **kwargs)
        await self._repair_send(ctx.author.id, send_fn)

    @app_commands.command(name="repair", description="Reparar un item dañado con Kit de reparación")
    @app_commands.autocomplete(item_name=repair_item_autocomplete)
    async def repair_slash(self, interaction: discord.Interaction, item_name: Optional[str] = None):
        """Reparar un item del inventario"""
        await interaction.response.defer()
        async def send_fn(*args, **kwargs):
            return await interaction.followup.send(*args, **kwargs)
        await self._repair_send(interaction.user.id, send_fn)


# ==================== SETUP ====================

async def setup(bot):
    """Cargar el cog de items"""
    await bot.add_cog(ItemsCog(bot))
