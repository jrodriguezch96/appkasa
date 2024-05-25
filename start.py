import requests
import json
import uuid
from datetime import datetime

# UUID
uuid = str(uuid.uuid4())

# Función para autenticar y obtener el token de acceso
def obtener_token(email, password):
    url = "https://wap.tplinkcloud.com"
    print("uuid", uuid)
    payload = {
        "method": "login",
        "params": {
            "appType": "Kasa_Android",
            "cloudUserName": email,
            "cloudPassword": password,
            "terminalUUID": uuid
        }
    }
    response = requests.post(url, json=payload)
    data = response.json()
    print("data", data)
    token = data['result']['token']
    print("token", token)
    return token

# Función para obtener la lista de dispositivos
def listar_dispositivos(token):
    url = f"https://wap.tplinkcloud.com?token={token}"
    payload = {
        "method": "getDeviceList"
    }
    response = requests.post(url, json=payload)
    data = response.json()
    print("data dispositivos", data)
    dispositivos = data['result']['deviceList']
    print("dispositivos", dispositivos)
    return dispositivos

# Función para obtener el consumo energético del dispositivo
def obtener_informacion_dispositivo(token, device_id, year, month):
    print("Entra a obtener_informacion_dispositivo")
    url = f"https://wap.tplinkcloud.com?token={token}"
    payload = {
        "method": "passthrough",
        "params": {
            "deviceId": device_id,
            "requestData": json.dumps({
                "system": {
                    "get_sysinfo": None
                },
                "emeter": {
                    "get_realtime": None,
                    "get_daystat": {
                        "year": year,
                        "month": month
                    }
                }
            })
        }
    }
    response = requests.post(url, json=payload)
    data = response.json()
    consumo = json.loads(data['result']['responseData'])
    return consumo

# Configura tu email y contraseña
email = "rodriguezjhonatanalexander@gmail.com"
password = "LINA210314"

# Obtén el token
token = obtener_token(email, password)

# Función para obtener el rango de fechas
def obtener_rango_fechas(token, device_id, start_date, end_date):
    current_date = start_date
    consumption_data = []

    while current_date <= end_date:
        year = current_date.year
        month = current_date.month
        infoEnchufe = obtener_informacion_dispositivo(token, device_id, year, month)
        if 'emeter' in infoEnchufe and 'get_daystat' in infoEnchufe['emeter']:
            day_stats = infoEnchufe['emeter']['get_daystat']['day_list']
            for day_stat in day_stats:
                stat_date = datetime(year=day_stat['year'], month=day_stat['month'], day=day_stat['day'])
                if start_date <= stat_date <= end_date:
                    consumption_data.append(day_stat)
        current_date = datetime(year=year + (month // 12), month=(month % 12) + 1, day=1)
    
    return consumption_data

# Define las fechas de inicio y fin
start_date = datetime(2024, 4, 23)
end_date = datetime(2024, 5, 25)

# Obtén la lista de dispositivos
# dispositivos = listar_dispositivos(token)

# # Muestra la lista de dispositivos y sus IDs
# for dispositivo in dispositivos:
#     print(f"Nombre: {dispositivo['alias']}, ID: {dispositivo['deviceId']}")

consumption_data = obtener_rango_fechas(token, "8006DABB0462CC97428C72D3DA80FCBA1EC0F1A4", start_date, end_date)

# Procesa y muestra el consumo diario en kWh
print("Consumo diario de energía (kWh):")
for day_stat in consumption_data:
    year = day_stat['year']
    month = day_stat['month']
    day = day_stat['day']
    energy_wh = day_stat['energy_wh']
    energy_kwh = energy_wh / 1000  # Convertir de Wh a kWh
    print(f"{year}-{month:02d}-{day:02d}: {energy_kwh:.3f} kWh")

# print("Energia Enchufe Lavadora", infoEnchufe)

# from flask import Flask, jsonify
# import asyncio
# from kasa import Discover, Credentials

# app = Flask(__name__)

# async def discover_devices():
#     try:
#         device = await Discover.discover_single(
#             "192.168.1.100",
#             credentials=Credentials("rodriguezjhonatanalexander@gmail.com", "LINA210314"),
#             timeout=20
#         )
#         await device.update()
#         return {
#             "is_on": device.is_on,
#             "alias": device.alias,
#             "power": device.emeter_realtime.power,
#             "current": device.emeter_realtime.current,
#             "voltage": device.emeter_realtime.voltage,
#             "emeter_today": device.emeter_today
#         }
#     except Exception as e:
#         return {
#             "error": "El dispositivo no se encuentra disponible o no se encuentra conectado a la red, se reintentará en 20 segundos."
#         }

# @app.route('/devices', methods=['GET'])
# def get_devices():
#     devices = asyncio.run(discover_devices())
#     return jsonify(devices)

# if __name__ == '__main__':
#     app.run(debug=True)