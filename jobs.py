# jobs.py
# Mapeo: rango -> lista de trabajos disponibles para ese rango
JOBS = {
    "Novato": [
        {"name": "Camillero", "salary": 120, "desc": "Tareas básicas y mover cosas."},
        {"name": "Asistente del Psiquiatra", "salary": 200, "desc": "Ayuda en consultas."}
    ],
    "Enfermo Básico": [
        {"name": "Analista de Crisis", "salary": 500, "desc": "Atiende casos difíciles."},
        {"name": "Guardia Sedante", "salary": 750, "desc": "Control de áreas y sedación."}
    ],
    "Enfermo Avanzado": [
        {"name": "Supervisor Psiquiátrico", "salary": 1500, "desc": "Supervisa al personal."},
        {"name": "Jefe de Terapia de Choque", "salary": 3000, "desc": "Dirige prácticas intensivas."}
    ],
    "Enfermo Supremo": [
        {"name": "Jefe del Distrito del Psicólogo", "salary": 7000, "desc": "Lidera un distrito entero."},
        {"name": "Director del Sanatorio", "salary": 12000, "desc": "Dirige el sanatorio."}
    ]
}
