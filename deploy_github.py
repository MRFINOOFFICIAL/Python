import os

# CONFIGURA ESTO
GITHUB_REPO = "https://github.com/MRFINOOFFICIAL/mi-bot-web.git"  # Reemplaza con tu repo
BRANCH = "master"  # O "master" según tu repo

def run_command(cmd):
    print(f"Ejecutando: {cmd}")
    result = os.system(cmd)
    if result != 0:
        print(f"Error ejecutando: {cmd}")
        exit(1)

# Inicializar git si no existe
if not os.path.exists(".git"):
    run_command("git init")

# Configura tu usuario si es necesario
run_command('git config --global user.name "MRFINOOFFICIAL"')
run_command('git config --global user.email "anthonyminijnr@gmail.com"')

# Agregar remoto si no existe
remotes = os.popen("git remote").read().split()
if "origin" not in remotes:
    run_command(f"git remote add origin {GITHUB_REPO}")

# Agregar todos los cambios
run_command("git add .")

# Crear commit
run_command('git commit -m "Actualizar web desde Replit"')

# Push
run_command(f"git push -u origin {BRANCH} --force")

print("✅ Web subida/actualizada en GitHub correctamente!")
