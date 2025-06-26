import requests


def classificar_zona(lat, lon, raio=200):
    query = f"""
    [out:json];
    (
    way(around:{raio},{lat},{lon})["landuse"];
    relation(around:{raio},{lat},{lon})["landuse"];
    );
    out tags center;
    """
    url = "https://overpass-api.de/api/interpreter"
    response = requests.post(url, data={"data": query})
    data = response.json()
    if data["elements"]:
        if landuse_tags := [
            elem["tags"].get("landuse")
            for elem in data["elements"]
            if "tags" in elem and "landuse" in elem["tags"]
        ]:
            return landuse_tags[0]
        else:
            return classificar_zona(lat, lon, raio + 50)
    else:
        return classificar_zona(lat, lon, raio + 50)


def obter_endereco(lat, lon):
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {"lat": lat, "lon": lon, "format": "json", "addressdetails": 1}
    headers = {
        "User-Agent": "MinhaAplicacaoPython/1.0 (seu-email@exemplo.com)"  # obrigatório
    }

    response = requests.get(url, params=params, headers=headers)
    dados = response.json()

    if "address" in dados:
        endereco = dados["address"]
        rua = endereco.get("road", "Rua não encontrada")
        tipo_zona = classificar_zona(lat, lon)
        return rua, tipo_zona
    else:
        return "Rua não encontrada", "desconhecida"
