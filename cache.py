# cache.py
# Pequeño cache en memoria para buffs/estados temporales entre comandos.
# Notar: es in-memory; si el bot reinicia, los buffs se pierden.

import time
from typing import Dict, Any

# Estructura:
# BUFFS[user_id] = {
#     "telefono_extra_time": int (segundos) o 0,
#     "linterna_boost_until": timestamp (float) o 0,
#     "chihuahua_passive_expires": timestamp o 0,
#     ...
# }
BUFFS: Dict[int, Dict[str, Any]] = {}

def set_buff(user_id: int, key: str, value):
    uid = int(user_id)
    BUFFS.setdefault(uid, {})
    BUFFS[uid][key] = value

def get_buff(user_id: int, key: str, default=None):
    uid = int(user_id)
    return BUFFS.get(uid, {}).get(key, default)

def clear_buff(user_id: int, key: str):
    uid = int(user_id)
    if uid in BUFFS and key in BUFFS[uid]:
        del BUFFS[uid][key]

def clear_all_user_buffs(user_id: int):
    uid = int(user_id)
    if uid in BUFFS:
        del BUFFS[uid]
