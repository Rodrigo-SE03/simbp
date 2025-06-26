from numba import njit
import numpy as np
import requests
import os
from loguru import logger


OPENROUTE_APIKEY = os.getenv("OPENROUTE_APIKEY")
EARTH_RADIUS_KM = 6371


def haversine(points: np.ndarray) -> np.ndarray:
    points_rad = np.radians(points)
    lat = points_rad[:, 0][:, np.newaxis]  # shape (N, 1)
    lon = points_rad[:, 1][:, np.newaxis]  # shape (N, 1)

    delta_lat = lat - lat.T  # shape (N, N)
    delta_lon = lon - lon.T  # shape (N, N)

    a = (
        np.sin(delta_lat / 2) ** 2
        + np.cos(lat) * np.cos(lat.T) * np.sin(delta_lon / 2) ** 2
    )
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


@njit
def route_distance(route, dist_matrix) -> float:
    total = 0.0
    prev = 0
    for i in range(len(route)):
        curr = route[i] + 1
        total += dist_matrix[prev, curr]
        prev = curr
    total += dist_matrix[prev, 0]
    return total


def get_distance_matrix(points: np.ndarray, initial=False) -> np.ndarray:
    if initial or len(points) > 59:
        return haversine(points)
    url = "https://api.openrouteservice.org/v2/matrix/driving-car"

    points_correcteds = np.empty_like(points)
    points_correcteds[:, 0] = points[:, 1]
    points_correcteds[:, 1] = points[:, 0]

    body = {
        "locations": points_correcteds.tolist(),
        "metrics": ["distance"],
        "units": "km",
    }
    headers = {
        "Accept": "application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8",
        "Authorization": OPENROUTE_APIKEY,
        "Content-Type": "application/json; charset=utf-8",
    }
    call = requests.post(url, json=body, headers=headers)
    if call.status_code != 200:
        logger.error(f"Error: {call.status_code} - {call.text}")
        return haversine(points)

    data = call.json()
    distances = np.array(data["distances"])
    for d in distances:
        if None in d:
            return haversine(points)
    return distances


def nearest_neighbor(
    origin, points: np.ndarray, initial=False
) -> tuple[list[int], np.ndarray]:

    dist_matrix = get_distance_matrix(np.vstack([origin, points]), initial=initial)
    np.fill_diagonal(dist_matrix, np.inf)

    unvisited = set(range(1, len(points) + 1))
    route = []
    current_idx = 0

    while unvisited:
        nearest = min(unvisited, key=lambda idx: dist_matrix[current_idx, idx])
        unvisited.remove(nearest)
        route.append(nearest - 1)
        current_idx = nearest
    return route, dist_matrix


@njit
def two_opt(route, dist_matrix, max_iterations=-1) -> list[int]:

    route_size = len(route)
    best = np.empty(route_size, dtype=np.int32)
    for i in range(route_size):
        best[i] = route[i]
    best_distance = route_distance(route, dist_matrix)

    iteration = 0
    improved = True

    while improved and (max_iterations < 0 or iteration < max_iterations):
        improved = False
        for i in range(1, route_size - 2):
            for j in range(i + 1, route_size):
                if j - i == 1:
                    continue  # vizinhos, pular

                new_route = np.empty(route_size, dtype=np.int32)
                new_route[:i] = best[:i]
                new_route[i : j + 1] = best[i : j + 1][::-1]
                new_route[j + 1 :] = best[j + 1 :]
                new_distance = route_distance(new_route, dist_matrix)

                if new_distance < best_distance:
                    best = new_route
                    best_distance = new_distance
                    improved = True
                    break

            if improved:
                break

        iteration += 1
    return best
