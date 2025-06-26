import asyncio
import random
import httpx
import osmnx as ox
from loguru import logger
import datetime

from utils.localization import obter_endereco
from database.mongo import get_collection

# URL do servidor
API_URL = "http://localhost:81"
IS_SIMULATION = True

# Configurações do sensor
MAX_DIST = 110
MIN_DIST_TO_CLEAN = 10

DIST_PER_READING = {
    "residential": [5, -1],  # Áreas residenciais - entupimento moderado
    "commercial": [4, -2],  # Áreas comerciais - entupimento um pouco menor
    "industrial": [7, -3],  # Áreas industriais - maior entupimento devido a resíduos
    "retail": [4, -1],  # Comércio varejista - similar ao comercial
    "construction": [6, -2],  # Áreas em construção - entupimento alto por detritos
    "forest": [1, 0],  # Florestas - pouco entupimento natural
    "farmland": [2, -1],  # Áreas agrícolas - entupimento baixo a moderado
    "allotments": [2, -1],  # Hortas urbanas - pouco entupimento
    "recreation_ground": [1, 0],  # Áreas recreativas - pouco entupimento
    "military": [3, -1],  # Áreas militares - entupimento moderado
    "quarry": [5, -2],  # Pedreiras - entupimento moderado a alto
    "cemetery": [1, 0],  # Cemitérios - pouco entupimento
    "garages": [4, -1],  # Garagens - entupimento moderado
    "brownfield": [6, -3],  # Terrenos abandonados - entupimento alto
    "greenfield": [1, 0],  # Terrenos verdes - pouco entupimento
    "plant_nursery": [2, -1],  # Viveiros de plantas - pouco entupimento
    "village_green": [1, 0],  # Áreas verdes em vilas - pouco entupimento
    "vineyard": [2, -1],  # Vinícolas - pouco entupimento
    "orchard": [2, -1],  # Pomares - pouco entupimento
    "greenhouse_horticulture": [2, -1],  # Estufas - pouco entupimento
    "salt_pond": [3, -1],  # Salinas - entupimento moderado
    "reservoir": [1, 0],  # Reservatórios - pouco entupimento
    "landfill": [8, -4],  # Aterros sanitários - entupimento muito alto
    "port": [5, -2],  # Portos comerciais - entupimento alto
    "default": [4, -1],  # Valor padrão para áreas não classificadas
}

MAX_DIST_GAIN_PER_READING = 5
MIN_DIST_GAIN_PER_READING = -1
PCT_TO_CLEAN = 0.3

NUM_SENSORS = 10
WAIT_TIME = 5

TICK_DAYS = 0
TICK_HOURS = 0
TICK_MINUTES = 15
TICK_SECONDS = 0

VERBOSE = False

## Configurações de Localização
# Coordenadas de Goiânia
LAT = -16.6869
LON = -49.2648

# Variação em torno de Goiânia (em graus)
LAT_RANGE = 0.06
LON_RANGE = 0.06
place = "Goiânia, Goiás, Brasil"

pause_event = asyncio.Event()
pause_event.set()


async def monitor_commands():
    loop = asyncio.get_event_loop()
    while True:
        cmd = await loop.run_in_executor(None, input, "")
        if cmd == "pause":
            pause_event.clear()
            logger.info("Simulação pausada.")
        elif cmd == "resume":
            pause_event.set()
            logger.info("Simulação retomada.")


class Sensor:
    def __init__(self, mac, lat, lon, rua, tipo_zona, verbose=False):
        self.verbose = verbose
        self.mac = mac
        self.lat = lat
        self.lon = lon
        self.rua = rua
        self.tipo_zona = tipo_zona
        self.dist = MAX_DIST

    async def send_reading(self, chuva, timestamp):
        if self.verbose:
            logger.info(
                f"Enviando leitura de {self.mac}: {self.dist}m, ({self.lat}, {self.lon})"
            )

        data = {
            "distancia": round(self.dist, 3),
            "latitude": self.lat,
            "longitude": self.lon,
            "rain_level": chuva,
            "rua": self.rua,
            "tipo_zona": self.tipo_zona,
            "mac": self.mac,
            "timestamp": timestamp.strftime("%d-%m-%Y %H:%M:%S"),
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{API_URL}/leituras", json=data)
                if response.status_code != 200:
                    response.raise_for_status()
            except httpx.RequestError as e:
                logger.error(f"Erro ao enviar leitura: {e}")
            except httpx.HTTPStatusError as e:
                logger.error(f"Erro de status HTTP: {e}")
            except Exception as e:
                logger.error(f"Erro inesperado: {e}")

    async def update_dist(self, chuva, timestamp):

        chuva_fator = [0.5, 1.0, 1.5, 2.0][chuva]
        max_dist_reading = DIST_PER_READING.get(
            self.tipo_zona, DIST_PER_READING["default"]
        )[0]
        min_dist_reading = DIST_PER_READING.get(
            self.tipo_zona, DIST_PER_READING["default"]
        )[1]

        ganho = random.uniform(-max_dist_reading, -min_dist_reading)
        ganho *= chuva_fator
        self.dist += ganho

        self.dist = min(self.dist, MAX_DIST)
        self.dist = MAX_DIST if random.random() < PCT_TO_CLEAN else max(self.dist, 0)
        await self.send_reading(chuva, timestamp)


def simular_chuva():
    p = random.random()
    if p < 0.6:
        return 0  # 60% sem chuva
    elif p < 0.85:
        return 1  # 25% fraca
    elif p < 0.97:
        return 2  # 12% moderada
    else:
        return 3  # 3% forte


existing_macs = set()


def gerar_mac_unico():
    while True:
        print(".", end="")
        mac = "".join(f"{random.randint(0, 255):02x}" for _ in range(6))
        if mac not in existing_macs:
            existing_macs.add(mac)
            return mac


async def main():
    sensores = []
    logger.info("Lendo sensores do banco de dados...")

    cursor = get_collection().find()
    timestamp = None
    for item in cursor:
        tmp_timestamp = datetime.datetime.strptime(
            item["timestamp"], "%d-%m-%Y %H:%M:%S"
        )
        if timestamp is None:
            timestamp = tmp_timestamp
        else:
            timestamp = max(timestamp, tmp_timestamp)

        mac = item["mac"]
        lat = item["latitude"]
        lon = item["longitude"]
        rua = item["rua"]
        tipo_zona = item["tipo_zona"]
        if mac not in existing_macs:
            existing_macs.add(mac)
            sensores.append(Sensor(mac, lat, lon, rua, tipo_zona, verbose=VERBOSE))

    if not sensores:
        logger.info("Iniciando simulação de sensores...")
        place = "Goiânia, Goiás, Brasil"
        G = ox.graph_from_place(place, network_type="drive")
        G_proj = ox.project_graph(G)
        G_proj = G_proj.to_undirected()

        points_proj = ox.utils_geo.sample_points(G_proj, NUM_SENSORS)  # type: ignore
        points_geo = points_proj.to_crs(epsg=4326)
        points = [[point.x, point.y] for point in points_geo.geometry]

        for idx in range(NUM_SENSORS):
            mac = gerar_mac_unico()
            while True:
                lat = points[idx][1]
                lon = points[idx][0]
                rua, tipo_zona = obter_endereco(lat, lon)
                if rua.startswith("."):
                    rua = rua[1:]
                if rua != "Rua não encontrada":
                    break
                points_proj = ox.utils_geo.sample_points(G_proj, 1)  # type: ignore
                points_geo = points_proj.to_crs(epsg=4326)
                p = [[point.x, point.y] for point in points_geo.geometry]
                points[idx] = p[0]

            sensores.append(Sensor(mac, lat, lon, rua, tipo_zona, verbose=VERBOSE))
        logger.info("Sensores criados com sucesso!")
        timestamp = datetime.datetime.now()

    asyncio.create_task(monitor_commands())
    logger.warning("Digite 'pause' para pausar a simulação e 'resume' para retomar.")

    if not timestamp:
        timestamp = datetime.datetime.now()

    while True:
        await pause_event.wait()
        logger.info("Iniciando envio de leituras...")
        chuva = simular_chuva()
        if not IS_SIMULATION:
            timestamp = datetime.datetime.now()
        await asyncio.gather(*(s.update_dist(chuva, timestamp) for s in sensores))
        timestamp += datetime.timedelta(
            days=TICK_DAYS, hours=TICK_HOURS, minutes=TICK_MINUTES, seconds=TICK_SECONDS
        )
        await asyncio.sleep(WAIT_TIME)


if __name__ == "__main__":
    asyncio.run(main())
