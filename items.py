# commands/items.py
import discord
from discord.ext import commands
from discord import app_commands
from db import (
    get_item_by_id, consume_item, get_inventory, add_item_to_user,
    repair_item, add_money, remove_item, add_buff, get_user
)
import random

SPECIAL_PELUCHES = [
    "Savi peluche",
    "Peluchito fino",
    "Pelucho elegante",
    "Peluche retro"
]

class ItemsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ------------- USE (prefijo) -------------
    @commands.command(name="use")
    async def use_prefix(self, ctx, item_id: int, target_item_id: int = None):
        """!use <item_id> [target_item_id]  — Usa un item del inventario"""
        await self._use_item(ctx, ctx.author.id, item_id, target_item_id, send_fn=lambda **kw: ctx.send(**kw))

    # ------------- USE (slash) -------------
    @app_commands.command(name="use", description="Usar un item de tu inventario")
    @app_commands.describe(item_id="ID del item en tu inventario", target_item_id="(Opcional) ID del item objetivo (ej. para kits)")
    async def use_slash(self, interaction: discord.Interaction, item_id: int, target_item_id: int = None):
        await interaction.response.defer()
        await self._use_item(interaction, interaction.user.id, item_id, target_item_id, send_fn=lambda **kw: interaction.followup.send(**kw))

    async def _use_item(self, ctx_or_interaction, user_id: int, item_id: int, target_item_id, send_fn):
        item = await get_item_by_id(item_id)
        if not item:
            return await send_fn(content="❌ Item no encontrado.")
        if str(item["user_id"]) != str(user_id):
            return await send_fn(content="❌ Ese item no te pertenece.")

        name = (item["item"] or "").lower()

        # ---- Kit de reparación ----
        if name in ("kit de reparación", "kit de reparacion", "kit de reparos"):
            if not target_item_id:
                return await send_fn(content="❗ Debes indicar el ID del item a reparar: `!use <id_del_kit> <id_del_item_a_reparar>`")
            target = await get_item_by_id(target_item_id)
            if not target or str(target["user_id"]) != str(user_id):
                return await send_fn(content="❌ Item objetivo no encontrado o no es tuyo.")
            # consumir el kit (usos)
            ok = await consume_item(item_id, 1)
            if not ok:
                return await send_fn(content="❌ No se pudo consumir el kit (quizá ya no tiene usos).")
            new_dur = await repair_item(target_item_id, 50, user_id)  # repara +50
            if new_dur is None:
                return await send_fn(content="❌ No se pudo reparar (permiso o item no encontrado).")
            return await send_fn(content=f"🛠️ Kit usado. Durabilidad nueva del item **{target['item']}** (id {target_item_id}): **{new_dur}%**")

        # ---- Paquete de peluches fino ----
        if name == "paquete de peluches fino":
            ok = await consume_item(item_id, 1)
            if not ok:
                return await send_fn(content="❌ No se pudo consumir el paquete.")
            # dar 3 peluches aleatorios (raridad variable)
            added = []
            for _ in range(3):
                p = random.choice(SPECIAL_PELUCHES)
                rarity = random.choice(["comun","raro","epico"])  # simple random
                await add_item_to_user(user_id, p, rarity, usos=1, durabilidad=100)
                added.append(f"{p} ({rarity})")
            return await send_fn(content=f"🎁 Abriste el paquete y obtuviste: {', '.join(added)}")

        # ---- x2 de dinero de mecha (buff) ----
        if name in ("x2 de dinero de mecha", "x2 de dinero de mecha "):
            ok = await consume_item(item_id, 1)
            if not ok:
                return await send_fn(content="❌ No se pudo consumir el item.")
            # agregamos buff 'mecha_x2' de 1 uso
            await add_buff(user_id, "mecha_x2", uses=1)
            return await send_fn(content="⚡ Activado **x2 de dinero de mecha** — se aplicará en la siguiente acción compatible (ej. Blackjack/mecha).")

        # ---- Danza de Saviteto (buff) ----
        if name == "danza de saviteto":
            ok = await consume_item(item_id, 1)
            if not ok:
                return await send_fn(content="❌ No se pudo consumir el item.")
            await add_buff(user_id, "danza", uses=1)
            return await send_fn(content="💃 Activada **Danza de Saviteto** — aumenta probabilidades en Blackjack para la próxima partida.")

        # ---- Kit genérico: usar para curar/dar dinero (ejemplo) ----
        if name in ("botiquín", "botiquin"):
            ok = await consume_item(item_id, 1)
            if not ok:
                return await send_fn(content="❌ No se pudo usar el botiquín.")
            await add_money(user_id, 100)
            return await send_fn(content="✅ Usaste el botiquín. Recibiste 100💰.")

        # ---- Teléfono: activar bonus de tiempo en work (ejemplo) ----
        if name == "teléfono" or name == "telefono":
            # este item lo dejamos como pasivo (si quieres que sea consumible, descomenta consume_item)
            return await send_fn(content="📱 El teléfono ofrece +5s automáticamente cuando haces `!work` — no es necesario usarlo manualmente.")

        # ---- Default: si item tiene 'usos' lo consumimos y mostramos info ----
        ok = await consume_item(item_id, 1)
        if not ok:
            return await send_fn(content="❌ No se pudo usar el item (quizá no tiene usos).")
        return await send_fn(content=f"✅ Usaste **{item['item']}** (id {item_id}). Si tenía efecto, se aplicó.")

    # ------------- REPAIR (prefijo) -------------
    @commands.command(name="repair")
    async def repair_prefix(self, ctx, target_item_id: int, using_kit_id: int = None):
        """!repair <id_item_objetivo> [id_kit]  — Repara pagando o usando kit"""
        await self._repair(ctx, ctx.author.id, target_item_id, using_kit_id, send_fn=lambda **kw: ctx.send(**kw))

    # ------------- REPAIR (slash) -------------
    @app_commands.command(name="repair", description="Reparar un item: usa kit o paga dinero")
    @app_commands.describe(target_item_id="ID del item a reparar", using_kit_id="(Opcional) ID del kit a consumir")
    async def repair_slash(self, interaction: discord.Interaction, target_item_id: int, using_kit_id: int = None):
        await interaction.response.defer()
        await self._repair(interaction, interaction.user.id, target_item_id, using_kit_id, send_fn=lambda **kw: interaction.followup.send(**kw))

    async def _repair(self, ctx_or_interaction, user_id: int, target_item_id: int, using_kit_id: int, send_fn):
        target = await get_item_by_id(target_item_id)
        if not target:
            return await send_fn(content="❌ Item objetivo no encontrado.")
        if str(target["user_id"]) != str(user_id):
            return await send_fn(content="❌ Ese item no es tuyo.")

        # si se pasa kit id: intentar usar kit (consumible)
        if using_kit_id:
            kit = await get_item_by_id(using_kit_id)
            if not kit or str(kit["user_id"]) != str(user_id):
                return await send_fn(content="❌ El kit no existe o no te pertenece.")
            name = (kit["item"] or "").lower()
            if name not in ("kit de reparación", "kit de reparacion", "kit de reparos"):
                return await send_fn(content="❌ Ese item no es un kit de reparación.")
            ok = await consume_item(using_kit_id, 1)
            if not ok:
                return await send_fn(content="❌ No se pudo consumir el kit.")
            new_dur = await repair_item(target_item_id, 50, user_id)
            if new_dur is None:
                return await send_fn(content="❌ Error reparando.")
            return await send_fn(content=f"🛠️ Usaste el kit. Durabilidad de **{target['item']}** ahora {new_dur}%.")

        # si no hay kit: permitir reparar pagando una cantidad fija (ej. 200)
        user = await get_user(user_id)
        cost = 200
        if user["dinero"] < cost:
            return await send_fn(content=f"❌ No tienes suficiente dinero para reparar (costo: {cost}💰).")
        # pagar y reparar parcialmente +40
        await add_money(user_id, -cost)
        new_dur = await repair_item(target_item_id, 40, user_id)
        if new_dur is None:
            return await send_fn(content="❌ No se pudo reparar (error).")
        return await send_fn(content=f"🔧 Pagaste {cost}💰 y reparaste **{target['item']}**. Durabilidad: {new_dur}%.")

    # --------- helper para listar inventario con ids (opcional) ----------
    @commands.command(name="inventory")
    async def inventory_prefix(self, ctx):
        inv = await get_inventory(ctx.author.id)
        if not inv:
            return await ctx.send("Tu inventario está vacío.")
        lines = [f"ID {i['id']} — {i['item']} ({i['rareza']}) usos:{i['usos']} dur:{i['durabilidad']}" for i in inv]
        # enviar en varios mensajes si es muy largo
        chunk = "\n".join(lines[:25])
        await ctx.send(f"📦 Inventario:\n{chunk}")
        if len(lines) > 25:
            await ctx.send("... (más items)")

async def setup(bot):
    await bot.add_cog(ItemsCog(bot))
