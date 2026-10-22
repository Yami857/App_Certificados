from functools import wraps

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from services.autenticacion import autenticar, en_modo_demo, usuarios_demo

bp = Blueprint("auth", __name__)


def requiere_login(vista):
    """Decorador que exige una sesión iniciada antes de ejecutar la vista.

    Si el usuario no ha entrado, lo manda a /login. Se usa con @requiere_login
    debajo de cada @bp.route que muestre datos.
    """

    @wraps(vista)
    def envuelta(*args, **kwargs):
        # La sesión guarda el correo de quien entró; si no está, no hay sesión.
        if not session.get("usuario_correo"):
            return redirect(url_for("auth.login"))
        return vista(*args, **kwargs)

    return envuelta


def solo_admin(vista):
    """Decorador que permite la vista solo si la sesión tiene rol "admin".

    Si el rol no es "admin", responde 403 (Prohibido). Se usa junto a
    @requiere_login para que, si además no hay sesión, primero mande a /login.
    """

    @wraps(vista)
    def envuelta(*args, **kwargs):
        if session.get("usuario_rol") != "admin":
            # abort(403) corta la petición; el manejador de abajo dibuja la página.
            abort(403)
        return vista(*args, **kwargs)

    return envuelta


@bp.app_errorhandler(403)
def sin_permiso(error):
    """Página amable para cualquier respuesta 403 de la aplicación."""
    return render_template("sin_permiso.html"), 403


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Pantalla de entrada: muestra el formulario y valida correo/contraseña."""
    # Si ya hay sesión, no tiene sentido volver a entrar.
    if session.get("usuario_correo"):
        return redirect(url_for("certificados.tablero"))

    error = ""
    correo = ""

    if request.method == "POST":
        correo = (request.form.get("correo") or "").strip()
        clave = request.form.get("clave") or ""

        usuario = autenticar(correo, clave)
        if usuario:
            # Sesión limpia: guardamos solo correo y rol, nunca la contraseña.
            session.clear()
            session["usuario_correo"] = usuario["correo"]
            session["usuario_rol"] = usuario["rol"]
            return redirect(url_for("certificados.tablero"))

        error = "Correo o contraseña incorrectos."

    return render_template(
        "login.html",
        error=error,
        correo=correo,
        modo_demo=en_modo_demo(),
        demo_usuarios=usuarios_demo(),
    )


@bp.route("/salir")
def salir():
    """Cierra la sesión y devuelve a la pantalla de entrada."""
    session.clear()
    flash("Has cerrado sesión.", "info")
    return redirect(url_for("auth.login"))
