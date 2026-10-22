"""Autenticación sencilla con sesiones de Flask.

Las credenciales NO están escritas en el código: se leen de variables de
entorno. Si en la máquina (o en Vercel) faltan esas variables, la app usa
credenciales de demostración y la pantalla de entrada muestra un aviso.

Variables esperadas:
- ADMIN_CORREO / ADMIN_CLAVE    -> rol "admin"
- USUARIO_CORREO / USUARIO_CLAVE -> rol "usuario"
"""

import hmac
import os
from typing import Any, Dict, List, Optional

# Credenciales de demostración: SOLO se usan cuando faltan las variables de
# entorno. Sirven para poder probar la app sin configurar nada.
CORREO_ADMIN_DEMO = "admin@academia.local"
CLAVE_ADMIN_DEMO = "Admin2026!"
CORREO_USUARIO_DEMO = "usuario@academia.local"
CLAVE_USUARIO_DEMO = "Usuario2026!"


def _leer_variable(nombre: str) -> Optional[str]:
    """Lee una variable de entorno y la devuelve limpia; None si está vacía."""
    valor = os.environ.get(nombre)
    if valor is None:
        return None
    valor = valor.strip()
    return valor or None


def _construir_usuario(
    prefijo: str,
    correo_demo: str,
    clave_demo: str,
    rol: str,
) -> Dict[str, Any]:
    """Arma un usuario leyendo <PREFIJO>_CORREO y <PREFIJO>_CLAVE del entorno.

    Si falta cualquiera de las dos variables, se usan las credenciales de
    demostración para ese usuario y se marca `es_demo = True`.
    """
    correo = _leer_variable(f"{prefijo}_CORREO")
    clave = _leer_variable(f"{prefijo}_CLAVE")

    if not correo or not clave:
        # Faltan datos: este usuario queda en modo demostración.
        return {
            "correo": correo_demo,
            "clave": clave_demo,
            "rol": rol,
            "es_demo": True,
        }

    return {
        "correo": correo,
        "clave": clave,
        "rol": rol,
        "es_demo": False,
    }


def obtener_usuarios() -> List[Dict[str, Any]]:
    """Devuelve la lista de usuarios disponibles (admin y usuario normal)."""
    return [
        _construir_usuario("ADMIN", CORREO_ADMIN_DEMO, CLAVE_ADMIN_DEMO, "admin"),
        _construir_usuario("USUARIO", CORREO_USUARIO_DEMO, CLAVE_USUARIO_DEMO, "usuario"),
    ]


def en_modo_demo() -> bool:
    """True si al menos un usuario está usando credenciales de demostración."""
    return any(usuario["es_demo"] for usuario in obtener_usuarios())


def usuarios_demo() -> List[Dict[str, str]]:
    """Datos de los usuarios en modo demostración, para mostrarlos en pantalla.

    Solo se devuelven correo, clave y rol: nunca se exponen credenciales
    configuradas de verdad por el administrador.
    """
    return [
        {"correo": usuario["correo"], "clave": usuario["clave"], "rol": usuario["rol"]}
        for usuario in obtener_usuarios()
        if usuario["es_demo"]
    ]


def autenticar(correo: str, clave: str) -> Optional[Dict[str, str]]:
    """Comprueba correo y contraseña contra la lista de usuarios.

    Retorna un diccionario con 'correo' y 'rol' si coinciden, o None si no.
    La contraseña nunca se devuelve ni se guarda en la sesión.
    """
    correo_limpio = (correo or "").strip().lower()
    clave_limpia = clave or ""

    for usuario in obtener_usuarios():
        correo_ok = hmac.compare_digest(
            correo_limpio.encode("utf-8"),
            usuario["correo"].strip().lower().encode("utf-8"),
        )
        clave_ok = hmac.compare_digest(
            clave_limpia.encode("utf-8"),
            usuario["clave"].encode("utf-8"),
        )
        if correo_ok and clave_ok:
            return {"correo": usuario["correo"], "rol": usuario["rol"]}

    return None
