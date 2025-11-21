# bosses.py
import random
from datetime import datetime, timedelta
from typing import Dict, Optional

BOSSES_DB = {
    "Mini-Boss": [
        {"name": "Goblin Capitán", "hp": 80, "ataque": 8, "rareza": "raro", "prob": 0.4, "rewards": {"dinero": (100, 200), "items": ["ID falso", "Chihuahua"]}},
        {"name": "Orco Guerrero", "hp": 100, "ataque": 10, "rareza": "raro", "prob": 0.3, "rewards": {"dinero": (150, 250), "items": ["Bastón de Staff"]}},
        {"name": "Bruja del Bosque", "hp": 70, "ataque": 12, "rareza": "epico", "prob": 0.2, "rewards": {"dinero": (200, 300), "items": ["Aconsejante Fantasma"]}},
    ],
    "Boss": [
        {"name": "Dragón Antiguo", "hp": 300, "ataque": 20, "rareza": "legendario", "prob": 0.15, "rewards": {"dinero": (1000, 2000), "items": ["Llave Maestra", "Mecha Enojado"]}},
        {"name": "Rey Esqueleto", "hp": 250, "ataque": 18, "rareza": "epico", "prob": 0.2, "rewards": {"dinero": (800, 1500), "items": ["Pistola vieja", "Máscara de Xfi"]}},
        {"name": "Demonio Oscuro", "hp": 280, "ataque": 22, "rareza": "legendario", "prob": 0.1, "rewards": {"dinero": (1200, 2500), "items": ["Llave Maestra"]}},
    ]
}

# Mapeo dinámico de armas basado en poder del item
WEAPON_STATS = {
    "Cinta adhesiva": {"hit_chance": 0.5, "damage": 5, "crit_chance": 0.05},
    "Botella de sedante": {"hit_chance": 0.55, "damage": 8, "crit_chance": 0.12},
    "Cuchillo oxidado": {"hit_chance": 0.7, "damage": 18, "crit_chance": 0.15},
    "Pistola vieja": {"hit_chance": 0.75, "damage": 35, "crit_chance": 0.2},
    "Botiquín": {"hit_chance": 0.3, "damage": 2, "crit_chance": 0.05},
    "Arma blanca artesanal": {"hit_chance": 0.75, "damage": 25, "crit_chance": 0.12},
    "Palo golpeador de parejas felices": {"hit_chance": 0.8, "damage": 30, "crit_chance": 0.1},
    "Savi peluche": {"hit_chance": 0.6, "damage": 12, "crit_chance": 0.3},
    "Hélice de ventilador": {"hit_chance": 0.45, "damage": 8, "crit_chance": 0.08},
    "Aconsejante Fantasma": {"hit_chance": 0.65, "damage": 30, "crit_chance": 0.25},
    "ID falso": {"hit_chance": 0.55, "damage": 22, "crit_chance": 0.35},
    "Máscara de Xfi": {"hit_chance": 0.7, "damage": 35, "crit_chance": 0.18},
    "Bastón de Staff": {"hit_chance": 0.75, "damage": 28, "crit_chance": 0.12},
    "Teléfono": {"hit_chance": 0.45, "damage": 12, "crit_chance": 0.1},
    "Chihuahua": {"hit_chance": 0.5, "damage": 5, "crit_chance": 0.2},
    "Mecha Enojado": {"hit_chance": 0.85, "damage": 40, "crit_chance": 0.25},
    "Linterna": {"hit_chance": 0.4, "damage": 7, "crit_chance": 0.05},
    "Llave Maestra": {"hit_chance": 0.3, "damage": 0, "crit_chance": 0.05},
    "Anillo oxidado": {"hit_chance": 0.45, "damage": 3, "crit_chance": 0.08},
    "Mapa antiguo": {"hit_chance": 0.5, "damage": 0, "crit_chance": 0.15},
    "Gafas de soldador": {"hit_chance": 0.6, "damage": 10, "crit_chance": 0.1},
    "Caja de cerillas": {"hit_chance": 0.35, "damage": 5, "crit_chance": 0.2},
    "Receta secreta": {"hit_chance": 0.55, "damage": 15, "crit_chance": 0.15},
    "Núcleo energético": {"hit_chance": 0.8, "damage": 50, "crit_chance": 0.3},
    "Fragmento Omega": {"hit_chance": 0.9, "damage": 60, "crit_chance": 0.4},
    "Traje ritual": {"hit_chance": 0.75, "damage": 45, "crit_chance": 0.35},
    "Placa de identificación": {"hit_chance": 0.6, "damage": 12, "crit_chance": 0.1},
    "Cable USB": {"hit_chance": 0.4, "damage": 2, "crit_chance": 0.05},
    "Garrafa de aceite": {"hit_chance": 0.35, "damage": 8, "crit_chance": 0.05},
    "Guitarra rota": {"hit_chance": 0.65, "damage": 16, "crit_chance": 0.2},
    # Items de tienda
    "Paquete de peluches fino": {"hit_chance": 0.55, "damage": 10, "crit_chance": 0.25},
    "x2 de dinero de mecha": {"hit_chance": 0.5, "damage": 5, "crit_chance": 0.1},
    "Danza de Saviteto": {"hit_chance": 0.7, "damage": 12, "crit_chance": 0.35},
    "Kit de reparación": {"hit_chance": 0.3, "damage": 1, "crit_chance": 0.05},
}

def get_random_boss(boss_type: str) -> Optional[Dict]:
    """Spawn a random boss based on probability"""
    if boss_type not in BOSSES_DB:
        return None
    
    candidates = BOSSES_DB[boss_type]
    for boss in candidates:
        if random.random() < boss["prob"]:
            return boss.copy()
    
    return random.choice(candidates).copy()

def calculate_player_damage(equipped_item: Optional[str] = None) -> tuple:
    """Calculate player damage based on equipped weapon"""
    if not equipped_item or equipped_item not in WEAPON_STATS:
        return (1, 3, 0.05)  # (hit_chance, base_damage, crit_chance)
    
    stats = WEAPON_STATS[equipped_item]
    return (stats["hit_chance"], stats["damage"], stats["crit_chance"])

def calculate_damage(base_damage: int, is_crit: bool = False) -> int:
    """Calculate damage with variance and critical hits"""
    variance = random.uniform(0.8, 1.2)
    damage = int(base_damage * variance)
    if is_crit:
        damage = int(damage * 1.5)
    return max(1, damage)

def resolve_player_attack(equipped_item: Optional[str] = None) -> tuple:
    """Resolve player attack, returns (hit: bool, damage: int, is_crit: bool)"""
    hit_chance, base_damage, crit_chance = calculate_player_damage(equipped_item)
    
    hit = random.random() < hit_chance
    is_crit = random.random() < crit_chance if hit else False
    damage = calculate_damage(base_damage, is_crit) if hit else 0
    
    return (hit, damage, is_crit)

def resolve_boss_attack(boss: Dict) -> tuple:
    """Resolve boss attack, returns (hit: bool, damage: int, is_crit: bool)"""
    boss_hit_chance = 0.6
    boss_crit_chance = 0.1
    
    hit = random.random() < boss_hit_chance
    is_crit = random.random() < boss_crit_chance if hit else False
    damage = calculate_damage(boss["ataque"], is_crit) if hit else 0
    
    return (hit, damage, is_crit)

async def get_boss_reward(boss: Dict) -> Dict:
    """Get rewards for defeating a boss"""
    dinero_range = boss["rewards"]["dinero"]
    dinero = random.randint(dinero_range[0], dinero_range[1])
    items = boss["rewards"]["items"]
    item = random.choice(items) if items else None
    
    return {"dinero": dinero, "item": item}
