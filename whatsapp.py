import os
import logging
from datetime import datetime
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from sheets import registrar_gasto, obtener_resumen

logger = logging.getLogger(__name__)

app = Flask(__name__)

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

# Estado de conversación por usuario (en memoria)
# Formato: { "whatsapp:+549...": { "estado": "monto"|"descripcion"|"categoria", "datos": {} } }
sesiones = {}

CATEGORIAS = [
    "1. 🍔 Comida",
    "2. 🚗 Transporte",
    "3. 🛒 Supermercado",
    "4. 💊 Salud",
    "5. 🎮 Entretenimiento",
    "6. 🏠 Hogar",
    "7. 📦 Otro",
]

MAPA_CATEGORIAS = {
    "1": "🍔 Comida",
    "2": "🚗 Transporte",
    "3": "🛒 Supermercado",
    "4": "💊 Salud",
    "5": "🎮 Entretenimiento",
    "6": "🏠 Hogar",
    "7": "📦 Otro",
}


def responder(texto):
    resp = MessagingResponse()
    resp.message(texto)
    return str(resp)


def nombre_desde_perfil(from_number, profile_name):
    """Usa el nombre del perfil de WhatsApp si está disponible."""
    return profile_name or from_number.replace("whatsapp:+", "+")


@app.route("/whatsapp", methods=["POST"])
def webhook():
    from_number = request.form.get("From", "")
    body = request.form.get("Body", "").strip()
    profile_name = request.form.get("ProfileName", "")

    nombre = nombre_desde_perfil(from_number, profile_name)
    username = from_number.replace("whatsapp:", "")
    sesion = sesiones.get(from_number, {})
    estado = sesion.get("estado")

    # Comandos globales
    if body.lower() in ["/start", "hola", "inicio", "menu", "menú"]:
        sesiones.pop(from_number, None)
        return responder(
            f"¡Hola {nombre}! 👋\n\n"
            "Soy tu bot de gastos.\n\n"
            "Comandos:\n"
            "💸 *gasto* — Registrar un gasto\n"
            "📊 *resumen* — Ver resumen del mes\n"
            "❌ *cancelar* — Cancelar operación"
        )

    if body.lower() == "cancelar":
        sesiones.pop(from_number, None)
        return responder("❌ Operación cancelada.")

    if body.lower() == "resumen":
        sesiones.pop(from_number, None)
        try:
            datos = obtener_resumen(username=username, nombre=nombre)
            if not datos:
                return responder("📭 No tenés gastos registrados este mes todavía.")
            texto = f"📊 *Resumen de {nombre} — {datetime.now().strftime('%B %Y')}*\n\n"
            total = 0
            for cat, subtotal in datos["por_categoria"].items():
                texto += f"{cat}: ${subtotal:,.2f}\n"
                total += subtotal
            texto += f"\n💰 *Total: ${total:,.2f}*"
            texto += f"\n📝 Gastos: {datos['cantidad']}"
            return responder(texto)
        except Exception as e:
            logger.error(f"Error resumen WhatsApp: {e}")
            return responder(f"❌ Error al obtener el resumen: {e}")

    # Flujo de registro de gasto
    if body.lower() in ["gasto", "/gasto"] or (not estado and _es_numero(body)):
        if _es_numero(body):
            monto = float(body.replace(",", "."))
            sesiones[from_number] = {"estado": "descripcion", "datos": {"monto": monto, "nombre": nombre, "username": username}}
            return responder(f"✅ Monto: ${monto:,.2f}\n\n📝 Escribí una descripción:")
        else:
            sesiones[from_number] = {"estado": "monto", "datos": {"nombre": nombre, "username": username}}
            return responder("💰 *Nuevo gasto*\n\nIngresá el monto:")

    if estado == "monto":
        if not _es_numero(body):
            return responder("❌ Ingresá solo el monto, por ejemplo: *250* o *1500.50*")
        monto = float(body.replace(",", "."))
        sesion["datos"]["monto"] = monto
        sesion["estado"] = "descripcion"
        sesiones[from_number] = sesion
        return responder(f"✅ Monto: ${monto:,.2f}\n\n📝 Escribí una descripción:")

    if estado == "descripcion":
        sesion["datos"]["descripcion"] = body
        sesion["estado"] = "categoria"
        sesiones[from_number] = sesion
        lista = "\n".join(CATEGORIAS)
        return responder(f"🏷️ Elegí una categoría (respondé con el número):\n\n{lista}")

    if estado == "categoria":
        numero = body.strip()
        categoria = MAPA_CATEGORIAS.get(numero)
        if not categoria:
            lista = "\n".join(CATEGORIAS)
            return responder(f"❌ Respondé con un número del 1 al 7:\n\n{lista}")

        datos = sesion["datos"]
        fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
        sesiones.pop(from_number, None)

        try:
            fila = registrar_gasto(
                nombre=datos["nombre"],
                username=datos["username"],
                monto=datos["monto"],
                descripcion=datos["descripcion"],
                categoria=categoria,
                fecha=fecha
            )
            return responder(
                f"✅ *¡Gasto registrado!*\n\n"
                f"👤 {datos['nombre']}\n"
                f"💰 ${datos['monto']:,.2f}\n"
                f"📝 {datos['descripcion']}\n"
                f"🏷️ {categoria}\n"
                f"📅 {fecha}\n\n"
                f"_Fila {fila} en la planilla_ 📊"
            )
        except Exception as e:
            logger.error(f"Error registrar WhatsApp: {e}")
            return responder(f"❌ Error al guardar el gasto: {e}")

    # Mensaje no reconocido
    return responder(
        "No entendí ese mensaje.\n\n"
        "Enviá *gasto* para registrar un gasto\n"
        "o *resumen* para ver el mes actual."
    )


def _es_numero(texto):
    try:
        val = float(texto.replace(",", "."))
        return val > 0
    except ValueError:
        return False


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
