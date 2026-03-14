# 🤖 Bot de Gastos — Telegram + Google Sheets

Registrá gastos desde Telegram directamente en tu planilla de Google Sheets.

---

## ✨ ¿Qué hace el bot?

- Recibe mensajes de Telegram con el monto, descripción y categoría de un gasto
- Registra automáticamente **quién** lo envió (nombre y @username)
- Guarda todo en tu Google Spreadsheet con fecha y hora
- Permite ver un **resumen del mes** por categoría

---

## 📋 Estructura de la planilla

El bot crea (o usa) una hoja llamada `Gastos` con estas columnas:

| Fecha | Nombre | Username | Monto | Descripción | Categoría |
|-------|--------|----------|-------|-------------|-----------|
| 13/03/2026 14:32 | Juan Pérez | @juanp | 250 | Almuerzo | 🍔 Comida |

---

## 🚀 Configuración paso a paso

### Paso 1 — Crear el bot en Telegram

1. Abrí Telegram y buscá **@BotFather**
2. Enviá `/newbot`
3. Elegí un nombre (ej: "Mis Gastos")
4. Elegí un username terminado en `bot` (ej: `misgastos_bot`)
5. BotFather te dará un **token** — copialo, lo necesitás

---

### Paso 2 — Crear credenciales de Google

1. Andá a [Google Cloud Console](https://console.cloud.google.com/)
2. Creá un proyecto nuevo (o usá uno existente)
3. Activá la **Google Sheets API**:
   - Menú → APIs & Services → Library
   - Buscá "Google Sheets API" → Enable
4. Creá una **Service Account**:
   - Menú → APIs & Services → Credentials
   - "+ Create Credentials" → Service Account
   - Poné un nombre (ej: `bot-gastos`)
   - Rol: **Editor** → Continuar → Listo
5. Descargá el JSON de credenciales:
   - Click en la service account creada
   - Pestaña "Keys" → Add Key → Create new key → JSON
   - Se descarga un archivo `.json` — guardalo bien

---

### Paso 3 — Compartir tu planilla con la Service Account

1. Abrí el archivo JSON descargado y copiá el valor de `client_email`
   (algo como `bot-gastos@mi-proyecto.iam.gserviceaccount.com`)
2. Abrí tu Google Spreadsheet
3. Hacé click en **Compartir** (arriba a la derecha)
4. Pegá ese email y dale permisos de **Editor**
5. Desactivá "Notificar a las personas" y confirmá

---

### Paso 4 — Configurar las variables de entorno

Copiá `.env.example` como `.env`:

```bash
cp .env.example .env
```

Editá `.env` y completá:

```env
TELEGRAM_TOKEN=tu_token_de_botfather

SPREADSHEET_ID=1gKS9iUdHLj8tJjH8X-_AlkpKmE7OnJ49FhiBVFAvC4Q
# (es la parte larga de la URL de tu planilla)

SHEET_NAME=Gastos

GOOGLE_CREDENTIALS_JSON={"type":"service_account",...}
# Pegá el contenido completo del JSON en una sola línea
```

> 💡 **Tip para el JSON**: Abrí el archivo descargado, seleccioná todo, y usá un conversor online para ponerlo en una sola línea, o ejecutá:
> ```bash
> cat credenciales.json | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin)))"
> ```

---

### Paso 5 — Instalar y ejecutar

```bash
# Instalá las dependencias
pip install -r requirements.txt

# Ejecutá el bot
python bot.py
```

---

## 🐳 Ejecutar con Docker (recomendado para producción)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
```

```bash
docker build -t gastos-bot .
docker run -d --env-file .env gastos-bot
```

---

## 💬 Cómo usar el bot

Una vez corriendo, en Telegram:

| Comando | Acción |
|---------|--------|
| `/start` | Presentación del bot |
| `/gasto` | Iniciar registro de un gasto |
| `/resumen` | Ver resumen del mes actual |
| `/cancelar` | Cancelar operación en curso |
| Enviar un número | Atajo para registrar gasto |

**Flujo de registro:**
1. Enviá `/gasto` (o directamente un número como `250`)
2. Ingresá el monto
3. Escribí una descripción breve
4. Elegí la categoría del menú

---

## 🏷️ Categorías disponibles

- 🍔 Comida
- 🚗 Transporte
- 🛒 Supermercado
- 💊 Salud
- 🎮 Entretenimiento
- 🏠 Hogar
- 📦 Otro

---

## 📁 Estructura del proyecto

```
gastos_bot/
├── bot.py              # Lógica principal del bot de Telegram
├── sheets.py           # Integración con Google Sheets
├── requirements.txt    # Dependencias Python
├── .env.example        # Template de variables de entorno
└── README.md           # Este archivo
```

---

## ❓ Preguntas frecuentes

**¿Puedo cambiar el nombre de la hoja?**
Sí, cambiá `SHEET_NAME` en el `.env`.

**¿El bot funciona en grupos?**
Sí, registra el nombre de quien envió el mensaje.

**¿Puedo agregar más categorías?**
Editá la lista `CATEGORIAS` en `bot.py`.

**¿Cómo hosteo el bot 24/7?**
Podés usar Railway, Render, o un VPS. El archivo Dockerfile de arriba te sirve para cualquiera de esos servicios.
