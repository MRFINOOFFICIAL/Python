# commands/rob.py
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View
from db import get_user, get_inventory, damage_item, add_money, remove_item, update_mission_progress, get_rob_cooldown, set_rob_cooldown
import random
from typing import Optional

# Mapa de stats por nombre del item (lowercase)
ITEM_STATS = {
    "cinta adhesiva":      {"categoria": "herramientas", "poder": 3},
    "botella de sedante":  {"categoria": "quimicos",    "poder": 6},
    "cuchillo oxidado":    {"categoria": "arma",       "poder": 18},
    "pistola vieja":       {"categoria": "arma",       "poder": 35},
    "botiquín":            {"categoria": "salud",      "poder": 2},
    "arma blanca artesanal":{"categoria":"arma",       "poder": 25},
    "palo golpeador de parejas felices": {"categoria":"arma","poder":30},
    "savi peluche":        {"categoria": "engano",     "poder": 10},
    "hélice de ventilador":{"categoria": "herramientas","poder": 8},
    "aconsejante fantasma": {"categoria":"engano",     "poder": 30},
    "id falso":            {"categoria": "engano",     "poder": 22},
    "máscara de xfi":      {"categoria": "engano",     "poder": 35},
    "bastón de staff":     {"categoria": "herramientas","poder": 28},
    "teléfono":            {"categoria": "tecnologia", "poder": 12},
    "chihuahua":           {"categoria": "mascota",    "poder": 5},
    "mecha enojado":       {"categoria": "arma",       "poder": 40},
    "linterna":            {"categoria": "herramientas","poder": 7},
    "llave maestra":       {"categoria": "herramientas","poder": 40},
    # Items de tienda
    "paquete de peluches fino": {"categoria": "consumible", "poder": 15},
    "x2 de dinero de mecha": {"categoria": "consumible", "poder": 12},
    "danza de saviteto": {"categoria": "consumible", "poder": 20},
    "poción de furia": {"categoria": "consumible", "poder": 18},
    "escudo mágico": {"categoria": "consumible", "poder": 10},
    "nektar antiguo": {"categoria": "consumible", "poder": 8},
    "kit de reparación": {"categoria": "consumible", "poder": 0},  # No es arma de combate
    # Items adicionales de explore
    "botiquín": {"categoria": "salud", "poder": 2},
    "traje ritual": {"categoria": "ropa", "poder": 35},
    "núcleo energético": {"categoria": "tecnologia", "poder": 45},
    "fragmento omega": {"categoria": "arma", "poder": 50},
    "anillo oxidado": {"categoria": "accesorio", "poder": 4},
    "mapa antiguo": {"categoria": "herramientas", "poder": 6},
    "gafas de soldador": {"categoria": "accesorio", "poder": 8},
    "caja de cerillas": {"categoria": "herramientas", "poder": 5},
    "receta secreta": {"categoria": "quimicos", "poder": 16},
    "placa de identificación": {"categoria": "accesorio", "poder": 7},
    "cable usb": {"categoria": "tecnologia", "poder": 9},
    "garrafa de aceite": {"categoria": "quimicos", "poder": 10},
    "guitarra rota": {"categoria": "arma", "poder": 20},  # Raro, más poder que comunes
}

# Sincronizar con explore.py
ITEM_STATS_EXPLORE = {
    "cinta adhesiva": {"categoria": "herramientas", "poder": 3},
    "botella de sedante": {"categoria": "quimicos", "poder": 6},
    "cuchillo oxidado": {"categoria": "arma", "poder": 18},
    "pistola vieja": {"categoria": "arma", "poder": 35},
    "botiquín": {"categoria": "salud", "poder": 2},
    "arma blanca artesanal": {"categoria": "arma", "poder": 25},
    "palo golpeador de parejas felices": {"categoria": "arma", "poder": 30},
    "savi peluche": {"categoria": "engano", "poder": 10},
    "hélice de ventilador": {"categoria": "herramientas", "poder": 8},
    "aconsejante fantasma": {"categoria": "engano", "poder": 30},
    "id falso": {"categoria": "engano", "poder": 22},
    "máscara de xfi": {"categoria": "engano", "poder": 35},
    "bastón de staff": {"categoria": "herramientas", "poder": 28},
    "teléfono": {"categoria": "tecnologia", "poder": 12},
    "chihuahua": {"categoria": "mascota", "poder": 5},
    "mecha enojado": {"categoria": "arma", "poder": 40},
    "linterna": {"categoria": "herramientas", "poder": 7},
    "llave maestra": {"categoria": "herramientas", "poder": 40},
    "anillo oxidado": {"categoria": "accesorio", "poder": 4},
    "mapa antiguo": {"categoria": "herramientas", "poder": 6},
    "gafas de soldador": {"categoria": "accesorio", "poder": 8},
    "caja de cerillas": {"categoria": "herramientas", "poder": 5},
    "receta secreta": {"categoria": "quimicos", "poder": 16},
    "núcleo energético": {"categoria": "tecnologia", "poder": 45},
    "fragmento omega": {"categoria": "arma", "poder": 50},
    "traje ritual": {"categoria": "ropa", "poder": 35},
    "placa de identificación": {"categoria": "accesorio", "poder": 7},
    "cable usb": {"categoria": "tecnologia", "poder": 9},
    "garrafa de aceite": {"categoria": "quimicos", "poder": 10},
    "guitarra rota": {"categoria": "arma", "poder": 12},
}

def weapon_power_from_rareza(rareza: Optional[str]):
    if not rareza:
        return 1
    if rareza.lower() == "comun":
        return 5
    if rareza.lower() == "raro":
        return 20
    if rareza.lower() == "epico":
        return 40
    return 1

class ChooseWeaponView(View):
    def __init__(self, user_id: int, items: list, timeout: int = 30):
        super().__init__(timeout=timeout)
        self.user_id = int(user_id)
        self.items = items  # list of inventory dicts
        self.result = None  # will hold chosen item dict or None for no-weapon
        # build buttons
        for it in items:
            label = (it["item"][:80])  # button label limit safe
            btn = Button(label=label, style=discord.ButtonStyle.secondary)
            # bind callback with default args to avoid late-binding
            async def _cb(interaction: discord.Interaction, item_id=it["id"], item_name=it["item"]):
                # only allow the owner
                if interaction.user.id != self.user_id:
                    await interaction.response.send_message("❌ Solo quien inició la acción puede elegir.", ephemeral=True)
                    return
                # set result
                self.result = {"id": item_id, "item": item_name}
                # edit message with placeholder (actual logic handled outside)
                await interaction.response.edit_message(content=f"Seleccionado: **{item_name}**. Procesando...", view=None, embed=None)
                # stop the view so on_timeout won't try to edit again
                self.stop()
            btn.callback = _cb
            self.add_item(btn)

        # add "sin arma" button
        no_btn = Button(label="Sin arma / intentar sin objetos", style=discord.ButtonStyle.danger)
        async def no_cb(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ Solo quien inició la acción puede elegir.", ephemeral=True)
                return
            self.result = None
            await interaction.response.edit_message(content="Seleccionado: **Sin arma**. Procesando...", view=None, embed=None)
            self.stop()
        no_btn.callback = no_cb
        self.add_item(no_btn)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    async def on_timeout(self):
        # Disable buttons on timeout
        for child in self.children:
            try:
                if hasattr(child, 'disabled'):
                    setattr(child, 'disabled', True)
            except Exception:
                pass
        # try to edit the original message to indicate timeout
        try:
            # there's no stored message here; caller should save and edit if needed.
            pass
        except Exception:
            pass

class RobCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _perform_rob(self, user_id: int, target_member: discord.Member, chosen_item_id: Optional[int], chosen_item_name: Optional[str]):
        """Core robber logic: returns result message string and whether success."""
        # Establecer cooldown
        await set_rob_cooldown(user_id, target_member.id)
        
        target = await get_user(target_member.id)
        if not target or target.get("dinero", 0) < 50:
            return False, "Esa persona no tienen suficiente dinero para robar."

        # determine power
        power = 0
        if chosen_item_id is not None:
            # try to grab item info from target's perspective not needed; we only need power
            # but ideally we trust passed name to look up stat
            key = chosen_item_name.lower() if chosen_item_name else ""
            stats = ITEM_STATS.get(key)
            if stats:
                power = stats.get("poder", 0)
            else:
                # fallback: try to get rarity from DB? (skip for simplicity) use base
                power = 10
        else:
            power = 0

        base_chance = 20 + int(power)
        success = random.randint(1, 100) <= base_chance

        if success:
            steal_amount = random.randint(50, min(600, target["dinero"] // 2))
            await add_money(user_id, steal_amount)
            await add_money(target_member.id, -steal_amount)
            # Actualizar progreso de misión "robar"
            await update_mission_progress(user_id)
            if chosen_item_id:
                # dañar item (reducir durabilidad)
                try:
                    await damage_item(chosen_item_id, 25)
                except Exception:
                    pass
            return True, f"🦹‍♀️ Robaste {steal_amount}💰 a {target_member.name} (¡éxito!) — tu item sufrió daño."
        else:
            loss = random.randint(10, 100)
            await add_money(user_id, -loss)
            return False, f"❌ Fallaste y perdiste {loss}💰. Ten cuidado."

    @commands.command(name="rob")
    @commands.cooldown(1, 300, commands.BucketType.user)
    async def rob_prefix(self, ctx, member: discord.Member):
        await self._start_rob_flow(ctx, ctx.author, member, is_interaction=False)

    @app_commands.command(name="rob", description="Robar a otro usuario (requiere mencionar)")
    @app_commands.describe(member="Usuario a robar")
    async def rob_slash(self, interaction: discord.Interaction, member: discord.Member):
        from datetime import datetime
        
        # Verificar cooldown de 5 minutos
        last_rob = await get_rob_cooldown(interaction.user.id)
        if last_rob and datetime.now() < last_rob:
            remaining = last_rob - datetime.now()
            mins, secs = divmod(int(remaining.total_seconds()), 60)
            return await interaction.response.send_message(f"⏳ Ya robaste hace poco. Espera {mins}m {secs}s.", ephemeral=True)
        
        await interaction.response.defer()
        await self._start_rob_flow(interaction, interaction.user, member, is_interaction=True)

    async def _start_rob_flow(self, ctx_or_interaction, user, member, is_interaction: bool):
        # preliminary checks
        if member.id == user.id:
            if is_interaction:
                return await ctx_or_interaction.followup.send("No puedes robarte a ti mismo.")
            return await ctx_or_interaction.send("No puedes robarte a ti mismo.")

        target = await get_user(member.id)
        if not target or target.get("dinero", 0) < 50:
            if is_interaction:
                return await ctx_or_interaction.followup.send("Esa persona no tiene suficiente dinero.")
            return await ctx_or_interaction.send("Esa persona no tiene suficiente dinero.")

        inv = await get_inventory(user.id)

        # enrich inventory with power if available
        for it in inv:
            key = it["item"].lower()
            if key in ITEM_STATS:
                it.setdefault("poder", ITEM_STATS[key].get("poder"))

        # build suggestion text
        if inv:
            lines = [f"{i['item']} ({i.get('rareza','?')}) — poder {i.get('poder', weapon_power_from_rareza(i.get('rareza')))}" for i in inv]
            suggestion_text = "Tus objetos:\n" + "\n".join(lines)
        else:
            suggestion_text = "No tienes objetos (puedes conseguirlos con `!explore`)."

        # If player has no items, go straight to attempt without choice
        if not inv:
            success, text = await self._perform_rob(user.id, member, None, None)
            final = f"{text}\n\n{suggestion_text}"
            if is_interaction:
                return await ctx_or_interaction.followup.send(final)
            return await ctx_or_interaction.send(final)

        # otherwise show buttons to choose item
        embed = discord.Embed(
            title="🔫 Elige objeto para el robo",
            description=f"{user.mention}, escoge el objeto que quieras usar (o 'Sin arma' para intentar sin objetos).\n\n{suggestion_text}",
            color=discord.Color.orange()
        )

        view = ChooseWeaponView(user.id, inv, timeout=30)

        # send message and capture message object depending on context
        sent_msg = None
        try:
            if is_interaction:
                await ctx_or_interaction.followup.send(embed=embed, view=view)
                # fetch original sent message to be able to edit on timeout; original_response gives the initial deferred response
                sent_msg = await ctx_or_interaction.original_response()
            else:
                sent_msg = await ctx_or_interaction.send(embed=embed, view=view)
        except Exception:
            # fallback: send plain text
            if is_interaction:
                await ctx_or_interaction.followup.send("❌ No pude enviar la interfaz para elegir item.")
            else:
                await ctx_or_interaction.send("❌ No pude enviar la interfaz para elegir item.")
            return

        # wait until view stops (choice made or timeout)
        await view.wait()

        # if user didn't choose (timeout) -> treat as cancel or "sin arma"
        chosen = view.result  # either dict with id/item or None

        # If view timed out without selection, edit message to show timeout (if possible) and stop
        if chosen is None:
            for child in view.children:
                if hasattr(child, 'disabled'):
                    setattr(child, 'disabled', True)

        # get chosen details
        chosen_item_id = chosen.get("id") if isinstance(chosen, dict) else None
        chosen_item_name = chosen.get("item") if isinstance(chosen, dict) else None

        # perform the rob
        success, text = await self._perform_rob(user.id, member, chosen_item_id, chosen_item_name)
        final_text = f"{text}\n\n{suggestion_text}"

        # try to edit the sent message (if we have it), otherwise send followup
        try:
            if sent_msg:
                try:
                    await sent_msg.edit(content=final_text, embed=None, view=None)
                    return
                except Exception:
                    pass
            # fallback: send new message
            if is_interaction:
                await ctx_or_interaction.followup.send(final_text)
            else:
                await ctx_or_interaction.send(final_text)
        except Exception:
            # last-resort: nothing we can do
            return

# setup
async def setup(bot):
    cog = RobCog(bot)
    await bot.add_cog(cog)
    # register slash (decorator usually does it, pero por seguridad:)
    try:
        bot.tree.add_command(app_commands.Command(name="rob", description="Robar a otro usuario (requiere mencionar)", callback=cog.rob_slash))
    except Exception:
        pass


