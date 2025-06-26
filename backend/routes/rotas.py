from database.mongo import aggregate, get_collection
from ia.GA.model import genetic_algorithm
from routes.models import RotaLimiar
from fastapi import APIRouter, BackgroundTasks, Response
from loguru import logger

router = APIRouter()

rota = None
distancia = None
origin = (-16.671244161185665, -49.23876761776484)
limiar = 44.0


@router.get("")
def calculate():
    global rota, distancia, flag_training
    flag_training = True
    try:
        pipeline = [
            {
                "$addFields": {
                    "timestamp": {
                        "$dateFromString": {
                            "dateString": "$timestamp",
                            "format": "%d-%m-%Y %H:%M:%S",
                        }
                    }
                }
            },
            {"$sort": {"mac": 1, "timestamp": -1}},
            {
                "$group": {
                    "_id": "$mac",
                    "distancia": {"$first": "$distancia"},
                    "latitude": {"$first": "$latitude"},
                    "longitude": {"$first": "$longitude"},
                },
            },
            {"$match": {"distancia": {"$lt": limiar}}},
        ]
        resultados = aggregate(get_collection(), pipeline)
        resultados_dict = {(p["latitude"], p["longitude"]): p for p in resultados}
        points = list(resultados_dict.keys())

        rota_points, distancia = genetic_algorithm(points, origin)
        rota = [resultados_dict[(points[i][0], points[i][1])] for i in rota_points]
        logger.info("Rota calculada")
        rota = [
            {
                "_id": "",
                "distancia": None,
                "latitude": origin[0],
                "longitude": origin[1],
            }
        ] + rota
        return rota, distancia

    except Exception as e:
        logger.exception(f"Error in calculate: {e}")
        return Response(status_code=500, content="Error calculating route.")


@router.post("/origin")
def update_origin(new_origin: tuple[float, float]):
    global origin
    if not isinstance(new_origin, tuple) or len(origin) != 2:
        return Response(
            status_code=400, content="Origin must be a tuple of (latitude, longitude)."
        )

    if not (-90 <= origin[0] <= 90) or not (-180 <= origin[1] <= 180):
        return Response(
            status_code=400, content="Invalid latitude or longitude values."
        )

    origin = new_origin
    return Response(status_code=200, content="Origin updated successfully.")


@router.post("/limiar")
def calculate_route(new_limiar: float):
    global limiar
    limiar = new_limiar
    limiar = 2000.0
