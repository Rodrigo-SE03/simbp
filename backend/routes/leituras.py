from routes.models import Dados
from database.mongo import get_collection, DESCENDING

from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Response, BackgroundTasks
from utils.localization import obter_endereco
from utils.openweather import get_rain

import datetime
import asyncio
import json

router = APIRouter()
clients: List[WebSocket] = []


async def notify_clients(data):
    for client in clients:
        try:
            await client.send_json(data)
        except:
            clients.remove(client)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            await asyncio.sleep(1)  # mantém a conexão aberta sem travar
    except WebSocketDisconnect:
        clients.remove(websocket)


@router.get("")
async def get_leituras():
    dados = get_collection().find()
    dados = list(dados)
    for dado in dados:
        dado["_id"] = str(dado["_id"])
        dado["rua"] = str(dado["rua"]) + " [" + str(dado["rua_id"]) + "]"
        dado.pop("rua_id")
    return dados


async def add_leitura(dados: Dados):
    if dados.rua is None:
        dados.rua, dados.tipo_zona = obter_endereco(dados.latitude, dados.longitude)

    timestamp = (
        datetime.datetime.strptime(dados.timestamp, "%d-%m-%Y %H:%M:%S")
        if dados.timestamp != None
        else datetime.datetime.now()
    )
    rain_level = (
        dados.rain_level
        if dados.rain_level != None
        else get_rain(dados.latitude, dados.longitude)
    )

    leitura_com_mac = get_collection().find_one({"rua": dados.rua, "mac": dados.mac})
    if leitura_com_mac:
        rua_id = leitura_com_mac.get("rua_id", 1)
    else:
        max_id_document = list(
            get_collection()
            .find({"rua": dados.rua})
            .sort("rua_id", DESCENDING)
            .limit(1)
        )
        max_id = max_id_document[0].get("rua_id", 0) if max_id_document else 0
        rua_id = max_id + 1

    dado = {
        "distancia": dados.distancia,
        "timestamp": timestamp.strftime("%d-%m-%Y %H:%M:%S"),
        "latitude": dados.latitude,
        "longitude": dados.longitude,
        "rain_level": rain_level,
        "rua": dados.rua,
        "tipo_zona": dados.tipo_zona,
        "rua_id": rua_id,
        "mac": dados.mac,
    }
    get_collection().insert_one(dado)
    dado.pop("_id")
    await notify_clients(json.dumps(dado))


@router.post("")
async def post_leitura(dados: Dados, background_tasks: BackgroundTasks):
    background_tasks.add_task(add_leitura, dados)
    return Response(status_code=200)
