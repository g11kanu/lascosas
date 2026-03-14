import os
import dotenv
import json
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

dotenv.load_dotenv(".env")

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
SHEET_NAME = os.environ.get("SHEET_NAME", "Gastos")


print("ID:", SPREADSHEET_ID)

print("id local:", os.environ.get("GOOGLE_CREDENTIALS_JSON"))


COLUMNAS = ["Fecha", "Nombre", "Username", "Monto", "Descripción", "Categoría"]


def get_service():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise ValueError("Falta la variable de entorno GOOGLE_CREDENTIALS_JSON")
    creds_data = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_data, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)


def inicializar_hoja():
    """Crea los encabezados si la hoja está vacía."""
    service = get_service()
    sheet = service.spreadsheets()

    result = sheet.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A1:F1"
    ).execute()

    values = result.get("values", [])
    if not values:
        sheet.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A1",
            valueInputOption="RAW",
            body={"values": [COLUMNAS]}
        ).execute()


def registrar_gasto(nombre, username, monto, descripcion, categoria, fecha):
    """
    Agrega una fila nueva en la hoja de cálculo.
    Retorna el número de fila donde se guardó.
    """
    service = get_service()
    sheet = service.spreadsheets()

    # Verificar/crear encabezados
    result = sheet.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A1:F1"
    ).execute()
    if not result.get("values"):
        sheet.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A1",
            valueInputOption="RAW",
            body={"values": [COLUMNAS]}
        ).execute()

    # Obtener la última fila con datos
    result = sheet.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A:A"
    ).execute()
    filas_existentes = len(result.get("values", []))
    nueva_fila = filas_existentes + 1

    fila_datos = [[fecha, nombre, f"@{username}", monto, descripcion, categoria]]

    sheet.values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A{nueva_fila}",
        valueInputOption="USER_ENTERED",
        body={"values": fila_datos}
    ).execute()

    return nueva_fila


def obtener_resumen(username, nombre):
    """
    Devuelve un resumen de gastos del mes actual para un usuario.
    Busca por username (@handle) o por nombre.
    """
    service = get_service()
    sheet = service.spreadsheets()

    result = sheet.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A:F"
    ).execute()

    rows = result.get("values", [])
    if len(rows) <= 1:
        return None

    mes_actual = datetime.now().strftime("%m/%Y")
    username_buscar = f"@{username}".lower()
    nombre_buscar = nombre.lower()

    por_categoria = {}
    cantidad = 0

    for row in rows[1:]:  # saltar encabezado
        if len(row) < 6:
            continue
        fecha_fila, nombre_fila, user_fila, monto_fila, _, categoria_fila = row

        # Verificar que sea del mes actual
        try:
            mes_fila = datetime.strptime(fecha_fila, "%d/%m/%Y %H:%M").strftime("%m/%Y")
        except Exception:
            continue

        if mes_fila != mes_actual:
            continue

        # Verificar que sea del usuario
        if (user_fila.lower() != username_buscar and
                nombre_fila.lower() != nombre_buscar):
            continue

        try:
            monto = float(str(monto_fila).replace(",", "."))
        except ValueError:
            continue

        cat = categoria_fila or "📦 Otro"
        por_categoria[cat] = por_categoria.get(cat, 0) + monto
        cantidad += 1

    if cantidad == 0:
        return None

    return {"por_categoria": por_categoria, "cantidad": cantidad}
