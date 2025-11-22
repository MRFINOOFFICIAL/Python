# commands/bosses.py
import discord
from discord.ext import commands
from discord import app_commands, ui
from datetime import datetime, timedelta
import random
from typing import Optional
from db import (
    get_active_boss, create_boss, damage_boss, deactivate_boss,
    set_event_channel, remove_event_channel, get_event_channels, get_all_active_bosses,
    set_equipped_item, get_equipped_item, set_fight_cooldown, get_fight_cooldown,
    add_money, get_user, add_item_to_user, get_inventory,
    remove_item, get_shop_item, add_experiencia, club_has_upgrade, get_pet_bonus_multiplier, add_pet_xp
)
from bosses import (
    get_random_boss, resolve_player_attack, resolve_boss_attack, get_boss_reward,
    get_boss_by_name, get_all_boss_names, get_available_bosses_by_type, get_weapon_benefit
)


# ==================== AUTOCOMPLETE ====================

async def equip_item_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete para equipar items"""
    try:
        inv = await get_inventory(interaction.user.id)
        if not inv:
            return []
        
        items = [item["item"] for item in inv]
        filtered = [name for name in items if current.lower() in name.lower()] if current else items
        
        return [app_commands.Choice(name=name[:100], value=name) for name in filtered[:25]]
    except Exception:
        return []

class FightActionView(ui.View):
    def __init__(self, user_id, interaction):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.interaction = interaction
        self.action = None
        self.selected_item = None
        self.damage_buff = False
        self.omega_charging = False  # Estado de carga de Fragmento Omega
    
    @ui.button(label="⚔️ Atacar", style=discord.ButtonStyle.red)
    async def attack_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer()
            return
        self.action = "attack"
        self.stop()
        await interaction.response.defer()
    
    @ui.button(label="🛡️ Defender", style=discord.ButtonStyle.blurple)
    async def defend_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer()
            return
        self.action = "defend"
        self.stop()
        await interaction.response.defer()
    
    @ui.button(label="📦 Usar Item", style=discord.ButtonStyle.green)
    async def item_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.defer()
            return
        try:
            inventory = await get_inventory(self.user_id)
            if not inventory:
                await interaction.response.send_message("❌ Inventario vacío", ephemeral=True)
                return
            options = [discord.SelectOption(label=f"{item['item']} (x{item['usos']})", value=str(item['id'])) for item in inventory[:25]]
            await interaction.response.send_message("Selecciona un item:", view=ItemSelectView(self.user_id, self, options), ephemeral=True)
        except Exception as e:
            print(f"Error con inventario: {e}")
            await interaction.response.send_message("❌ Error al cargar inventario", ephemeral=True)

class ItemSelectView(ui.View):
    def __init__(self, user_id, fight_view, options):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.fight_view = fight_view
        
        if options:
            select = ui.Select(placeholder="Elige un item para usar", options=options, min_values=1, max_values=1)
            select.callback = self.select_item
            self.add_item(select)
    
    async def select_item(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.defer()
            return
        select = self.children[0]
        if hasattr(select, 'values') and select.values:
            self.fight_view.action = "use_item"
            self.fight_view.selected_item = select.values[0]
        self.fight_view.stop()
        await interaction.response.defer()

async def boss_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete for boss names - shows all bosses"""
    try:
        all_bosses = get_all_boss_names()
        filtered = [name for name in all_bosses if current.lower() in name.lower()] if current else all_bosses
        return [app_commands.Choice(name=name, value=name) for name in filtered[:25]]
    except Exception as e:
        print(f"Error en autocomplete: {e}")
        return []

class BossesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spawn_tasks = {}

    async def _fight_internal(self, user_id, guild_id, interaction):
        """Interactive fight logic - user chooses actions each turn"""
        # Get all active bosses for this server
        active_bosses = await get_all_active_bosses(guild_id)
        if not active_bosses:
            return await interaction.followup.send("❌ No hay jefe activo en este servidor.", ephemeral=True)
        
        # Get the first (or only) active boss
        boss_data = active_bosses[0]
        boss_name = boss_data["boss_name"]
        
        # Get full boss info from bosses.py
        boss = get_boss_by_name(boss_name)
        if not boss:
            return await interaction.followup.send("❌ Jefe no encontrado.", ephemeral=True)
        
        # Update boss HP from DB
        boss["current_hp"] = boss_data["current_hp"]
        boss["max_hp"] = boss_data["max_hp"]
        
        cooldown = await get_fight_cooldown(user_id, guild_id)
        if cooldown and datetime.fromisoformat(cooldown.isoformat()) > datetime.now() - timedelta(minutes=2):
            return await interaction.followup.send("⏳ Debes esperar 2 minutos entre peleas.", ephemeral=True)
        
        equipped = await get_equipped_item(user_id)
        weapon = equipped["item_name"] if equipped else None
        
        player_hp = 100
        boss_hp = boss["current_hp"]
        turn = 1
        fight_log = []
        defend_next = False
        omega_charging = False
        
        await interaction.followup.send("⚔️ ¡Iniciando combate!")
        
        while player_hp > 0 and boss_hp > 0 and turn <= 30:
            embed = discord.Embed(title=f"⚔️ Turno {turn}: {boss['name']}", color=discord.Color.red())
            embed.add_field(name="Tu HP", value=f"{player_hp} HP", inline=True)
            embed.add_field(name="HP Jefe", value=f"{boss_hp}/{boss['max_hp']} HP", inline=True)
            embed.add_field(name="Elige tu acción:", value="⚔️ Atacar | 🛡️ Defender | 📦 Usar Item", inline=False)
            embed.add_field(name="Último evento", value=fight_log[-1] if fight_log else "...", inline=False)
            
            view = FightActionView(user_id, interaction)
            view.omega_charging = omega_charging  # Transferir estado de preparación
            msg = await interaction.followup.send(embed=embed, view=view)
            await view.wait()
            omega_charging = view.omega_charging  # Actualizar estado para próximo turno
            
            if view.action == "attack":
                player_hit, player_dmg, player_crit = resolve_player_attack(weapon)
                if player_hit:
                    if view.damage_buff:
                        player_dmg = int(player_dmg * 1.5)
                        view.damage_buff = False
                    # Bonus por upgrade Armería Mejorada
                    if await club_has_upgrade(user_id, "Armería Mejorada"):
                        player_dmg = int(player_dmg * 1.15)
                    boss_hp -= player_dmg
                    crit_text = " ¡CRÍTICO!" if player_crit else ""
                    fight_log.append(f"⚔️ Golpeaste por {player_dmg}{crit_text}")
                else:
                    fight_log.append(f"❌ ¡Fallaste tu ataque!")
            elif view.action == "defend":
                defend_next = True
                fight_log.append(f"🛡️ ¡Te preparaste para defender!")
            elif view.action == "use_item" and view.selected_item:
                try:
                    item_id = int(view.selected_item)
                    inventory = await get_inventory(user_id)
                    used_item = None
                    for item in inventory:
                        if item['id'] == item_id:
                            used_item = item
                            break
                    
                    if used_item:
                        item_name = used_item['item'].lower()
                        item_type = used_item.get('categoria', 'consumible')
                        
                        # Efectos especiales por nombre de item (explore)
                        if "núcleo energético" in item_name:
                            boss_hp -= 80
                            fight_log.append(f"⚡ ¡Núcleo Energético explotó! -80 HP al jefe!")
                        elif "fragmento omega" in item_name:
                            if not view.omega_charging:
                                # Primera carga: modo preparación
                                view.omega_charging = True
                                fight_log.append(f"✨ ¡PREPARANDO FRAGMENTO OMEGA! Usa de nuevo el próximo turno para SUPER ATAQUE (120 dmg)!")
                            else:
                                # Segunda carga: super ataque activado
                                boss_hp -= 120
                                view.omega_charging = False
                                fight_log.append(f"⚡⚡ ¡¡SUPER ATAQUE FRAGMENTO OMEGA!! -120 HP CRÍTICO al jefe!")
                        elif "pistola vieja" in item_name or "máscara de xfi" in item_name:
                            boss_hp -= 50
                            fight_log.append(f"🔫 ¡Ataque crítico! -50 HP al jefe!")
                        elif "llave maestra" in item_name:
                            player_hp = min(100, player_hp + 40)
                            boss_hp -= 30
                            fight_log.append(f"🔑 ¡Magia de la llave! +40 HP y -30 HP jefe!")
                        elif "aconsejante fantasma" in item_name:
                            view.damage_buff = True
                            fight_log.append(f"👻 ¡El fantasma te fortalece! +50% daño próximo!")
                        elif "chihuahua" in item_name:
                            attack_dmg = random.randint(15, 35)
                            boss_hp -= attack_dmg
                            fight_log.append(f"🐕 ¡El chihuahua ataca! -{attack_dmg} HP al jefe!")
                        elif "traje ritual" in item_name:
                            player_hp = min(100, player_hp + 60)
                            defend_next = True
                            fight_log.append(f"🎭 ¡Ritual mágico! +60 HP y defensa!")
                        elif "botella de sedante" in item_name or "cuchillo oxidado" in item_name:
                            boss_hp -= 35
                            fight_log.append(f"💀 ¡Ataque efectivo! -{35} HP al jefe!")
                        elif "palo golpeador" in item_name or "arma blanca artesanal" in item_name:
                            boss_hp -= 40
                            fight_log.append(f"⚒️ ¡Golpe contundente! -{40} HP al jefe!")
                        elif "mecha enojado" in item_name:
                            boss_hp -= 70
                            fight_log.append(f"🤖 ¡Mecha Enojado te ayuda! -{70} HP al jefe!")
                        elif item_type == "consumible":
                            player_hp = min(100, player_hp + 50)
                            fight_log.append(f"📦 ¡Recuperaste 50 HP!")
                        elif "poción de furia" in item_name:
                            boss_hp -= 60
                            fight_log.append(f"🧪 ¡Poción de Furia lanzada! -{60} HP al jefe!")
                        elif item_type == "consumible_damage":
                            boss_hp -= 40
                            fight_log.append(f"💥 ¡Infligiste 40 de daño directo!")
                        elif "nektar antiguo" in item_name:
                            player_hp = min(100, player_hp + 100)
                            fight_log.append(f"🍹 ¡Nektar Antiguo! +100 HP (recuperación completa)!")
                        elif "danza de saviteto" in item_name or item_type == "consumible_buff":
                            view.damage_buff = True
                            fight_log.append(f"⚡ ¡Tu próximo ataque inflige +50% de daño!")
                        elif item_type == "consumible_shield":
                            defend_next = True
                            fight_log.append(f"🛡️ ¡Te protegerás del próximo ataque!")
                        elif item_type == "arma":
                            boss_hp -= 35
                            fight_log.append(f"⚔️ ¡Arma equipada! -{35} HP al jefe!")
                        elif item_type == "herramientas":
                            player_hp = min(100, player_hp + 20)
                            fight_log.append(f"🔧 ¡Herramienta usada! +20 HP!")
                        elif item_type == "salud":
                            player_hp = min(100, player_hp + 40)
                            fight_log.append(f"⚕️ ¡Recuperaste 40 HP!")
                        elif item_type == "mascota":
                            dmg = random.randint(10, 25)
                            boss_hp -= dmg
                            fight_log.append(f"🐾 ¡Tu mascota ataca! -{dmg} HP al jefe!")
                        elif item_type == "engano":
                            view.damage_buff = True
                            fight_log.append(f"🎭 ¡Engaño! +50% daño próximo!")
                        elif item_type == "quimicos":
                            boss_hp -= 30
                            fight_log.append(f"🧪 ¡Químico! -{30} HP al jefe!")
                        elif item_type == "tecnologia":
                            boss_hp -= 25
                            fight_log.append(f"⚙️ ¡Tecnología! -{25} HP al jefe!")
                        else:
                            player_hp = min(100, player_hp + 25)
                            fight_log.append(f"📦 ¡Usaste item! +25 HP!")
                        
                        await remove_item(item_id)
                except Exception as e:
                    print(f"Error usando item: {e}")
                    fight_log.append(f"❌ Error al usar item")
            
            if boss_hp <= 0:
                break
            
            boss_hit, boss_dmg, boss_crit = resolve_boss_attack(boss)
            shield_active = defend_next
            if defend_next:
                boss_dmg = int(boss_dmg * 0.5)
                defend_next = False
            
            if boss_hit:
                player_hp -= boss_dmg
                crit_text = " ¡CRÍTICO!" if boss_crit else ""
                if shield_active:
                    fight_log.append(f"🛡️ ¡Escudo Mágico activado! {boss['name']} golpeó por {boss_dmg}{crit_text} (daño reducido 50%)")
                else:
                    fight_log.append(f"💥 {boss['name']} golpeó por {boss_dmg}{crit_text}")
            else:
                fight_log.append(f"🛡️ {boss['name']} falló")
            
            turn += 1
            try:
                await msg.delete()
            except:
                pass
        
        await damage_boss(guild_id, boss_name, max(0, boss_hp))
        await set_fight_cooldown(user_id, guild_id)
        
        if boss_hp <= 0:
            from bosses import BOSS_WEAPONS
            reward = await get_boss_reward(boss)
            
            # Aplicar bonificador de mascota
            dinero_base = reward["dinero"]
            pet_bonus = await get_pet_bonus_multiplier(user_id)
            dinero_final = int(dinero_base * pet_bonus)
            await add_money(user_id, dinero_final)
            
            # Dar XP a mascota
            await add_pet_xp(user_id, 25)
            
            # Agregar XP por victoria
            xp_reward = 150
            if await club_has_upgrade(user_id, "Sala de Meditación"):
                xp_reward = int(xp_reward * 1.30)  # +30% XP
            await add_experiencia(user_id, xp_reward)
            embed = discord.Embed(title="🏆 ¡VICTORIA!", color=discord.Color.gold())
            embed.add_field(name="⚔️ Enemigo derrotado", value=f"```{boss['name']}```", inline=False)
            
            # Mostrar recompensa con bonus
            if pet_bonus > 1.0:
                bonus_text = f"\n✨ (+{int((pet_bonus-1)*100)}% por mascota)"
            else:
                bonus_text = ""
            embed.add_field(
                name="🎁 Recompensas",
                value=f"💰 ```{dinero_final:,}``` dinero{bonus_text}\n⭐ ```{xp_reward}``` XP",
                inline=False
            )
            
            # Recompensa: arma única del boss (con probabilidades según tipo)
            boss_weapon = BOSS_WEAPONS.get(boss_name)
            boss_type = boss.get("type", "Mini-Boss")
            
            # Probabilidad de obtener el arma especial
            weapon_chance = 0.0
            if boss_type == "Mini-Boss":
                weapon_chance = 0.30  # 30% para mini bosses
            elif boss_type == "Boss":
                weapon_chance = 0.10  # 10% para bosses
            elif boss_type == "Especial":
                weapon_chance = 1.0   # 100% para bosses especiales
            
            if boss_weapon and random.random() < weapon_chance:
                await add_item_to_user(user_id, boss_weapon, rareza="maestro", usos=1, durabilidad=100, categoria="arma", poder=55)
                embed.add_field(name="⚔️ ARMA ESPECIAL", value=f"**{boss_weapon}** (maestro - +20% cofres al explorar)", inline=False)
            elif boss_weapon:
                # No consiguió el arma, pero se lo notificamos
                embed.add_field(name="⚔️ Arma especial", value=f"Fallaste: {boss_weapon} no se obtuvo (probabilidad de {int(weapon_chance*100)}%)", inline=False)
            
            # Recompensa adicional: items normales
            if reward["item"]:
                await add_item_to_user(user_id, reward["item"], rareza=boss["rareza"], usos=1, durabilidad=100, categoria="arma", poder=15)
                embed.add_field(name="Item", value=f"📦 {reward['item']}", inline=False)
            
            await deactivate_boss(guild_id, boss_name)
            channels = await get_event_channels(guild_id)
            for ch_id in channels:
                try:
                    ch = self.bot.get_channel(ch_id)
                    if ch:
                        await ch.send(f"🏆 <@{user_id}> derrotó a **{boss['name']}**!")
                except:
                    pass
        else:
            embed = discord.Embed(title="💀 DERROTA", color=discord.Color.dark_red())
            embed.add_field(name="⚔️ Te derrotó", value=f"```{boss['name']}```", inline=False)
            lost_money = random.randint(10, 50)
            embed.add_field(name="💸 Pérdida", value=f"```-{lost_money} dinero```", inline=False)
        
        embed.add_field(name="Eventos", value="\n".join(fight_log[-5:]) or "...", inline=False)
        await interaction.followup.send(embed=embed)

    @commands.command(name="fight")
    async def fight_prefix(self, ctx):
        """!fight - Pelea contra el jefe activo"""
        class DummyInteraction:
            def __init__(self, ctx):
                self.ctx = ctx
            class ResponseHelper:
                def __init__(self, ctx):
                    self.ctx = ctx
                async def send_message(self, *args, **kwargs):
                    await self.ctx.send(*args, **kwargs)
                async def defer(self):
                    pass
            class FollowupHelper:
                def __init__(self, ctx):
                    self.ctx = ctx
                async def send(self, *args, **kwargs):
                    await self.ctx.send(*args, **kwargs)
            def __init__(self, ctx):
                self.ctx = ctx
                self.response = self.ResponseHelper(ctx)
                self.followup = self.FollowupHelper(ctx)
        dummy = DummyInteraction(ctx)
        await self._fight_internal(ctx.author.id, ctx.guild.id, dummy)

    @app_commands.command(name="fight", description="Pelea contra el jefe activo")
    async def fight_slash(self, interaction: discord.Interaction):
        """Fight the active boss"""
        await interaction.response.defer()
        await self._fight_internal(interaction.user.id, interaction.guild_id, interaction)

    @commands.command(name="bossinfo")
    async def bossinfo_prefix(self, ctx):
        """!bossinfo - Ver información del jefe activo"""
        guild_id = ctx.guild.id
        active_bosses = await get_all_active_bosses(guild_id)
        
        if not active_bosses:
            return await ctx.send("❌ No hay jefe activo.")
        
        boss_data = active_bosses[0]
        boss = get_boss_by_name(boss_data.get("boss_name"))
        
        if not boss:
            return await ctx.send("❌ Jefe no encontrado.")
        
        embed = discord.Embed(title=f"📊 {boss.get('name', 'Unknown')}", color=discord.Color.yellow())
        embed.add_field(name="Tipo", value=boss.get("type", "?"), inline=True)
        embed.add_field(name="HP", value=f"{boss.get('hp', '?')} / {boss.get('max_hp', '?')}", inline=True)
        embed.add_field(name="Ataque", value=boss.get("ataque", "?"), inline=True)
        embed.add_field(name="Usa !fight o /fight para atacar", value="⚔️", inline=False)
        
        await ctx.send(embed=embed)

    @app_commands.command(name="bossinfo", description="Ver información del jefe activo")
    async def bossinfo_slash(self, interaction: discord.Interaction):
        """Get info about the active boss"""
        guild_id = interaction.guild_id
        active_bosses = await get_all_active_bosses(guild_id)
        
        if not active_bosses:
            return await interaction.response.send_message("❌ No hay jefe activo.", ephemeral=True)
        
        boss_data = active_bosses[0]
        boss = get_boss_by_name(boss_data.get("boss_name"))
        
        if not boss:
            return await interaction.response.send_message("❌ Jefe no encontrado.", ephemeral=True)
        
        embed = discord.Embed(title=f"📊 {boss.get('name', 'Unknown')}", color=discord.Color.yellow())
        embed.add_field(name="HP Actual", value=f"{boss_data.get('current_hp', '?')} / {boss_data.get('max_hp', '?')}", inline=True)
        embed.add_field(name="Ataque", value=boss.get("ataque", "?"), inline=True)
        embed.add_field(name="Rareza", value=boss.get("rareza", "?"), inline=True)
        embed.add_field(name="Usa !fight o /fight para atacar", value="⚔️", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.command(name="equip")
    async def equip_prefix(self, ctx, *, item_name: str):
        """!equip <item> - Equipar un arma"""
        user_id = ctx.author.id
        
        await set_equipped_item(user_id, 0, item_name)
        
        embed = discord.Embed(title="✅ Item Equipado", color=discord.Color.blue())
        embed.add_field(name="Arma", value=item_name, inline=False)
        embed.add_field(name="Beneficio", value=get_weapon_benefit(item_name), inline=False)
        
        await ctx.send(embed=embed)

    @app_commands.command(name="equip", description="Equipar un arma")
    @app_commands.describe(item_name="Nombre del item a equipar")
    @app_commands.autocomplete(item_name=equip_item_autocomplete)
    async def equip_slash(self, interaction: discord.Interaction, item_name: str):
        """Equip a weapon"""
        await interaction.response.defer()
        user_id = interaction.user.id
        
        await set_equipped_item(user_id, 0, item_name)
        
        embed = discord.Embed(title="✅ Item Equipado", color=discord.Color.blue())
        embed.add_field(name="Arma", value=item_name, inline=False)
        embed.add_field(name="Beneficio", value=get_weapon_benefit(item_name), inline=False)
        
        await interaction.followup.send(embed=embed)

    @commands.command(name="spawnboss")
    @commands.has_guild_permissions(administrator=True)
    async def spawnboss_prefix(self, ctx, boss_type: str):
        """!spawnboss Mini-Boss/Boss - Forzar spawn de jefe (Admin)"""
        guild_id = ctx.guild.id
        
        if boss_type not in ["Mini-Boss", "Boss"]:
            return await ctx.send("❌ Tipo debe ser 'Mini-Boss' o 'Boss'")
        
        boss = get_random_boss(boss_type)
        if not boss:
            return await ctx.send("❌ Error al generar jefe")
        
        await create_boss(guild_id, boss["name"], boss["hp"])
        
        embed = discord.Embed(title="🚨 ¡JEFE APARECE!", color=discord.Color.red())
        embed.add_field(name="Nombre", value=boss["name"], inline=True)
        embed.add_field(name="Tipo", value=boss_type, inline=True)
        embed.add_field(name="HP", value=boss["hp"], inline=True)
        embed.add_field(name="Ataque", value=boss["ataque"], inline=True)
        embed.add_field(name="Rareza", value=boss["rareza"], inline=True)
        embed.add_field(name="Usa !fight o /fight para pelear", value="⚔️", inline=False)
        
        # Enviar al canal actual
        await ctx.send(embed=embed)
        
        # Luego enviar a los canales configurados
        channels = await get_event_channels(guild_id)
        for ch_id in channels:
            try:
                ch = self.bot.get_channel(ch_id)
                if ch and ch.id != ctx.channel.id:
                    await ch.send(embed=embed)
            except:
                pass

    @app_commands.command(name="spawnboss", description="Forzar spawn de jefe (Admin)")
    @app_commands.describe(tipo="Tipo de jefe: Mini-Boss, Boss o Especial", jefe="O selecciona un jefe específico")
    @app_commands.autocomplete(jefe=boss_autocomplete)
    async def spawnboss_slash(self, interaction: discord.Interaction, tipo: Optional[str] = None, jefe: Optional[str] = None):
        """Force spawn a boss"""
        if not interaction.guild:
            return await interaction.response.send_message("❌ Este comando solo funciona en servidores", ephemeral=True)
        if not interaction.permissions.administrator:
            return await interaction.response.send_message("❌ Solo admins", ephemeral=True)
        
        # Especiales solo para el owner del bot o admins
        SPECIAL_BOSSES = ["Psicólogo Loco", "Médico Misterioso", "Enfermera de Hierro", "Director del Caos", "Fino"]
        
        guild_id = interaction.guild_id
        boss = None
        is_special = False
        
        if jefe:
            boss = get_boss_by_name(jefe)
            if not boss:
                return await interaction.response.send_message(f"❌ Jefe '{jefe}' no encontrado", ephemeral=True)
            is_special = jefe in SPECIAL_BOSSES
        elif tipo and tipo in ["Mini-Boss", "Boss", "Especial"]:
            is_special = tipo == "Especial"
            boss = get_random_boss(tipo)
            if not boss:
                return await interaction.response.send_message(f"❌ Error al generar jefe de tipo {tipo}", ephemeral=True)
        else:
            return await interaction.response.send_message("❌ Debes elegir un tipo (Mini-Boss, Boss, Especial) o un jefe específico", ephemeral=True)
        
        await create_boss(guild_id, boss["name"], boss["hp"])
        
        embed = discord.Embed(title="🚨 ¡JEFE APARECE!", color=discord.Color.red())
        embed.add_field(name="Nombre", value=boss["name"], inline=True)
        embed.add_field(name="Rareza", value=boss["rareza"], inline=True)
        embed.add_field(name="HP", value=boss["hp"], inline=True)
        embed.add_field(name="Ataque", value=boss["ataque"], inline=True)
        embed.add_field(name="Dinero", value=f"{boss['rewards']['dinero'][0]}-{boss['rewards']['dinero'][1]}", inline=True)
        embed.add_field(name="Usa !fight o /fight para pelear", value="⚔️", inline=False)
        
        # Enviar al canal actual primero
        await interaction.response.send_message(embed=embed)
        
        # Luego enviar a los canales configurados
        channels = await get_event_channels(guild_id)
        for ch_id in channels:
            try:
                ch = self.bot.get_channel(ch_id)
                if ch and ch.id != interaction.channel_id:
                    await ch.send(embed=embed)
            except:
                pass

async def setup(bot):
    await bot.add_cog(BossesCog(bot))
