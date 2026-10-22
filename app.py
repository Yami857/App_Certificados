import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from controllers.auth import bp as auth_bp
from controllers.certificados import bp as certificados_bp

# Cargar las variables del archivo .env (solo existe en la máquina local).
load_dotenv()

# Carpeta donde vive este archivo: las rutas no dependen
# desde dónde se ejecute la app (producción/Vercel).
BASE_DIR = Path(__file__).resolve().parent

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "views"),
    static_folder=str(BASE_DIR / "views" / "static"),
)

# Clave para firmar la cookie de sesión. Se lee del entorno y, si no existe,
# se genera una aleatoria: nunca queda escrita en el código.
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

# Tope de tamaño para una petición completa (formularios + archivos).
# Vercel rechaza las peticiones de más de 4.5 MB, así que nos quedamos justo
# por debajo: 4.5 MB. Si se supera, Flask responde 413 y la app muestra un aviso.
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024 + 512 * 1024

# Registrar rutas y controladores
app.register_blueprint(auth_bp)
app.register_blueprint(certificados_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
