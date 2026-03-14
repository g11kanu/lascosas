import os
import logging
import dotenv
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from sheets import registrar_gasto, obtener_resumen

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

dotenv.load_dotenv(".env")

print("Token:", os.environ.get("TELEGRAM_TOKEN"))
print("Archivo .env encontrado:", os.path.exists(".env"))
print("Directorio actual:", os.getcwd())

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# Estados de la conversación
MONTO, DESCRIPCION, CATEGORIA = range(3)

CATEGORIAS = [
    ["🍔 Comida", "🚗 Transporte"],
    ["🛒 Supermercado", "💊 Salud"],
    ["🎮 Entretenimiento", "🏠 Hogar"],
    ["📦 Otro"],
]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = update.effective_user.first_name
    await update.message.reply_text(
        f"¡Hola {nombre}! 👋\n\n"
        "Soy tu bot de gastos. Puedo registrar tus gastos en Google Sheets.\n\n"
        "Comandos disponibles:\n"
        "💸 /gasto — Registrar un nuevo gasto\n"
        "📊 /resumen — Ver tu resumen del mes\n"
        "❓ /ayuda — Ver ayuda\n\n"
        "También podés mandarme directamente el monto, por ejemplo: *150.50*",
        parse_mode="Markdown"
    )


async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Cómo usar el bot:*\n\n"
        "1️⃣ Enviá `/gasto` o directamente un número\n"
        "2️⃣ Ingresá el monto (ej: `250` o `1500.50`)\n"
        "3️⃣ Escribí una descripción breve\n"
        "4️⃣ Elegí la categoría\n\n"
        "✅ El gasto queda registrado en Google Sheets con tu nombre y la fecha.",
        parse_mode="Markdown"
    )


async def iniciar_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💰 *Nuevo gasto*\n\nIngresá el monto:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return MONTO


async def recibir_monto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip().replace(",", ".")
    try:
        monto = float(texto)
        if monto <= 0:
            raise ValueError
        context.user_data["monto"] = monto
        await update.message.reply_text(
            f"✅ Monto: *${monto:,.2f}*\n\n📝 Ahora escribí una descripción breve del gasto:",
            parse_mode="Markdown"
        )
        return DESCRIPCION
    except ValueError:
        await update.message.reply_text(
            "❌ Eso no parece un número válido. Ingresá solo el monto, por ejemplo: `250` o `1500.50`",
            parse_mode="Markdown"
        )
        return MONTO


async def recibir_descripcion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["descripcion"] = update.message.text.strip()
    await update.message.reply_text(
        "🏷️ Elegí una categoría:",
        reply_markup=ReplyKeyboardMarkup(CATEGORIAS, one_time_keyboard=True, resize_keyboard=True)
    )
    return CATEGORIA


async def recibir_categoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    categoria = update.message.text.strip()
    # Limpiar emoji de la categoría si viene con él
    for fila in CATEGORIAS:
        for cat in fila:
            if cat in categoria or categoria in cat:
                categoria = cat
                break

    user = update.effective_user
    nombre = f"{user.first_name} {user.last_name or ''}".strip()
    username = user.username or nombre

    monto = context.user_data["monto"]
    descripcion = context.user_data["descripcion"]
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

    try:
        fila = registrar_gasto(
            nombre=nombre,
            username=username,
            monto=monto,
            descripcion=descripcion,
            categoria=categoria,
            fecha=fecha
        )
        await update.message.reply_text(
            f"✅ *¡Gasto registrado!*\n\n"
            f"👤 *Quién:* {nombre}\n"
            f"💰 *Monto:* ${monto:,.2f}\n"
            f"📝 *Descripción:* {descripcion}\n"
            f"🏷️ *Categoría:* {categoria}\n"
            f"📅 *Fecha:* {fecha}\n\n"
            f"_Guardado en fila {fila} de la planilla_ 📊",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
    except Exception as e:
        logger.error(f"Error al registrar gasto: {e}")
        await update.message.reply_text(
            "❌ Hubo un error al guardar el gasto. Verificá la configuración de Google Sheets.\n\n"
            f"Error: `{str(e)}`",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )

    context.user_data.clear()
    return ConversationHandler.END


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Operación cancelada.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    nombre = f"{user.first_name} {user.last_name or ''}".strip()
    username = user.username or nombre

    try:
        datos = obtener_resumen(username=username, nombre=nombre)
        if not datos:
            await update.message.reply_text(
                "📭 No tenés gastos registrados este mes todavía.",
            )
            return

        texto = f"📊 *Resumen de {nombre} — {datetime.now().strftime('%B %Y')}*\n\n"
        total = 0
        for cat, subtotal in datos["por_categoria"].items():
            texto += f"{cat}: *${subtotal:,.2f}*\n"
            total += subtotal
        texto += f"\n💰 *Total: ${total:,.2f}*"
        texto += f"\n📝 *Gastos registrados: {datos['cantidad']}*"

        await update.message.reply_text(texto, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error al obtener resumen: {e}")
        await update.message.reply_text(
            f"❌ Error al obtener el resumen: `{str(e)}`",
            parse_mode="Markdown"
        )


async def mensaje_directo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Si el usuario manda un número directamente, empezar el flujo de gasto."""
    texto = update.message.text.strip().replace(",", ".")
    try:
        monto = float(texto)
        if monto > 0:
            context.user_data["monto"] = monto
            await update.message.reply_text(
                f"💰 Monto detectado: *${monto:,.2f}*\n\n📝 Escribí una descripción:",
                parse_mode="Markdown"
            )
            return DESCRIPCION
    except ValueError:
        pass
    await update.message.reply_text(
        "No entendí ese mensaje. Usá /gasto para registrar un gasto o /ayuda para ver los comandos."
    )
    return ConversationHandler.END


def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("Falta la variable de entorno TELEGRAM_TOKEN")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("gasto", iniciar_gasto),
            MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje_directo),
        ],
        states={
            MONTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_monto)],
            DESCRIPCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_descripcion)],
            CATEGORIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_categoria)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ayuda", ayuda))
    app.add_handler(CommandHandler("resumen", resumen))
    app.add_handler(conv_handler)

    logger.info("Bot iniciado...")
    app.run_polling()


if __name__ == "__main__":
    main()
