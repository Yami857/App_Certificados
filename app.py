from pathlib import Path

from flask import Flask
from controllers.certificados import bp as certificados_bp

# Carpeta donde vive este archivo: las rutas no dependen
# desde dónde se ejecute la app (producción/Vercel).
BASE_DIR = Path(__file__).resolve().parent

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "views"),
    static_folder=str(BASE_DIR / "views" / "static"),
)
app.secret_key = "academia_certificados_secret_key"

# Registrar rutas y controladores
app.register_blueprint(certificados_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
