from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import leituras, coordenadas, lstm, rotas
from database.mongo import init_db
from loguru import logger

from ia.GA.model import genetic_algorithm
from ia.LSTM.model import load_model
import asyncio


async def background_start():
    logger.info("Carregando Modelo LSTM...")
    try:
        lstm.lstm_model, lstm.lstm_scaler, lstm.lstm_le = load_model()
    except Exception as e:
        logger.warning(f"Erro ao carregar modelo: {e}")
        lstm.create_lstm_model()
    logger.info("LSTM pronta")

    logger.info("Compilando Algoritmo Genético...")
    population = [(float(i), float(i)) for i in range(3)]
    origin = (3.0, 3.0)
    genetic_algorithm(population, origin, initial=True)
    logger.info("Algoritmo Genético Pronto")


async def startup_event(_):
    init_db()
    asyncio.create_task(background_start())
    yield


app = FastAPI(lifespan=startup_event)  # type: ignore

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def home():
    return {"message": "Hello World"}


app.include_router(leituras.router, prefix="/leituras", tags=["leituras"])
app.include_router(coordenadas.router, prefix="/coordenadas", tags=["coordenadas"])
app.include_router(lstm.router, prefix="/lstm", tags=["lstm"])
app.include_router(rotas.router, prefix="/rotas", tags=["rotas"])

# uvicorn main:app --reload --host 0.0.0.0 --port 81
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=81, reload=True)
