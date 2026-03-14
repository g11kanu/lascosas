import os
import json
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv
load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
SHEET_NAME = os.environ.get("SHEET_NAME", "Gastos")

COLUMNAS = ["Fecha", "Nombre", "Username", "Monto", "Descripción", "Categoría"]


def get_service():
    creds_file = os.environ.get("GOOGLE_CREDENTIALS_FILE")
    if not creds_file:
        raise ValueError("Falta GOOGLE_CREDENTIALS_FILE en el .env")
    if not os.path.exists(creds_file):
        raise ValueError(f"No se encontró el archivo: {creds_file}")

    # Leer el JSON directamente y reparar \n literales en private_key
    with open(creds_file, "r", encoding="utf-8") as f:
        creds_data = json.load(f)

    # Reparar private_key si tiene \n como texto literal en vez de salto real
    if "private_key" in creds_data:
        creds_data["private_key"] = creds_data["private_key"].replace("\\n", "\n")

    creds = Credentials.from_service_account_info(creds_data, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)


def registrar_gasto(nombre, username, monto, descripcion, categoria, fecha):
    service = get_service()
    sheet = service.spreadsheets()

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

    for row in rows[1:]:
        if len(row) < 6:
            continue
        fecha_fila, nombre_fila, user_fila, monto_fila, _, categoria_fila = row

        try:
            mes_fila = datetime.strptime(fecha_fila, "%d/%m/%Y %H:%M").strftime("%m/%Y")
        except Exception:
            continue

        if mes_fila != mes_actual:
            continue

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
