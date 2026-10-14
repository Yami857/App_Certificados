from flask import Flask
from controllers.certificados import bp as certificados_bp

app = Flask(
    __name__,
    template_folder="views",
    static_folder="views/static",
)
app.secret_key = "academia_certificados_secret_key"

# Registrar rutas y controladores
app.register_blueprint(certificados_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
