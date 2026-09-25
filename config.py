import os

UAZAPI_URL   = os.environ.get("UAZAPI_URL", "https://benitechlab.uazapi.com")
UAZAPI_TOKEN = os.environ["UAZAPI_TOKEN"]

AUDIO_URL = "https://drive.google.com/uc?export=download&id=1sa5sVC28jQZwgu6gL-cl26Cxwha0qYEm"

INSTAGRAM_URL = "https://www.instagram.com/oficialigortimo"

MENSAGEM_BOTOES = (
    "Cuidar da saúde em casa ficou muito mais fácil. "
    "Ouve o áudio e me fala o que achou 👆"
)

BOTAO_1 = f"🎯 Quero saber mais|{INSTAGRAM_URL}"
BOTAO_2 = "❌ Não tenho interesse|sair"

DELAY_ENTRE_MSGS = 4
DELAY_MIN = 90
DELAY_MAX = 150

DATA_DIR = os.environ.get("DATA_DIR", "data")
os.makedirs(DATA_DIR, exist_ok=True)

PLANILHA    = os.environ.get("PLANILHA", "banco de dados saude no lar.xlsx")
OPTOUT_FILE = os.path.join(DATA_DIR, "optout.txt")
LOG_FILE    = os.path.join(DATA_DIR, "enviados.txt")
FALHAS_FILE = os.path.join(DATA_DIR, "falhas.txt")
