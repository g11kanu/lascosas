import threading
import os
import logging
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

def run_telegram():
    from bot import main
    main()

def run_whatsapp():
    from whatsapp import app
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    t1 = threading.Thread(target=run_telegram, daemon=True)
    t2 = threading.Thread(target=run_whatsapp, daemon=True)

    t1.start()
    t2.start()

    t1.join()
    t2.join()
