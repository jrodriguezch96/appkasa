from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import json
import uuid
from datetime import datetime, timedelta
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import numpy as np
import time

app = Flask(__name__)

CORS(app)

# Configura tus credenciales y el ID de la hoja de cálculo
SPREADSHEET_ID = '12bKGFHQjl8U49zRiapfDC1gtU4HANSCvEuB_AExxpO8'
RANGE_NAME = 'Hoja 1!A:B'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'credentials.json'

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('sheets', 'v4', credentials=credentials)
sheet = service.spreadsheets()

# UUID
uuid_str = str(uuid.uuid4())

# Variables globales para almacenar el token y su expiración
token = None
token_expiration = None

def obtener_token(email, password, retries=3, delay=60):
    print("Entra a obtener_token", flush=True)
    global token, token_expiration
    url = "https://wap.tplinkcloud.com"
    payload = {
        "method": "login",
        "params": {
            "appType": "Kasa_Android",
            "cloudUserName": email,
            "cloudPassword": password,
            "terminalUUID": uuid_str
        }
    }
    for attempt in range(retries):
        response = requests.post(url, json=payload)
        data = response.json()
        if data['error_code'] == 0:
            token = data['result']['token']
            token_expiration = datetime.now() + timedelta(hours=1)
            return token
        elif data['error_code'] == -20004:
            print(f"Rango de limites excedido. Reintentando en {delay} segundos...", flush=True)
            time.sleep(delay)
        else:
            raise Exception(f"Error al obtener token: {data['msg']}")
    raise Exception("Número máximo de intentos excedido. Por favor, inténtelo de nuevo más tarde.")

def get_valid_token(email, password):
    global token, token_expiration
    if token is None or datetime.now() >= token_expiration:
        token = obtener_token(email, password)
    return token

def obtener_informacion_dispositivo(token, app_server_url, device_id):
    url = f"{app_server_url}?token={token}"
    print("url obtener informacion dispositivo", url, flush=True)
    payload = {
        "method": "passthrough",
        "params": {
            "deviceId": device_id,
            "requestData": json.dumps({
                "emeter": {
                    "get_realtime": {}
                }
            })
        }
    }
    response = requests.post(url, json=payload)
    data = response.json()
    return json.loads(data['result']['responseData'])

def listar_dispositivos(token):
    url = f"https://wap.tplinkcloud.com?token={token}"
    payload = {
        "method": "getDeviceList"
    }
    response = requests.post(url, json=payload)
    data = response.json()
    # print("data dispositivos", data, flush=True)
    dispositivos = data['result']['deviceList']
    # print("dispositivos", dispositivos, flush=True)
    return dispositivos

def leer_datos():
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])
    if not values:
        return pd.DataFrame(columns=['Fecha', 'Consumo'])
    else:
        df = pd.DataFrame(values[1:], columns=values[0])
        df['Consumo'] = df['Consumo'].str.replace(',', '.').astype(float)
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce').dt.strftime('%Y-%m-%d')
        if df['Fecha'].isnull().any():
            print("Error al convertir algunas fechas. Verifica los datos en la hoja de cálculo.", flush=True)
        df = df.dropna(subset=['Fecha'])
        return df

@app.route('/get_excel_data', methods=['GET'])
def get_excel_data():
    try:
        fecha_desde = request.args.get('fecha_desde')
        fecha_hasta = request.args.get('fecha_hasta')
        
        df = leer_datos()

        if fecha_desde:
            fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d')
            df = df[df['Fecha'] >= fecha_desde.strftime('%Y-%m-%d')]

        if fecha_hasta:
            fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d')
            df = df[df['Fecha'] <= fecha_hasta.strftime('%Y-%m-%d')]

        return jsonify(df.to_dict(orient='records'))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_real_time_data', methods=['GET'])
def get_real_time_data():
    try:
        email = "rodriguezjhonatanalexander@gmail.com"
        password = "CXB4fwviF2pN$7P"
        token = get_valid_token(email, password)
        dispositivos = listar_dispositivos(token)
        device_id = "8006DABB0462CC97428C72D3DA80FCBA1EC0F1A4"
        app_server_url = None
        
        for dispositivo in dispositivos:
            if dispositivo["deviceId"] == device_id:
                app_server_url = dispositivo["appServerUrl"]
                break
        
        if app_server_url is None:
            return jsonify({'error': 'Dispositivo no encontrado.'}), 404

        data = obtener_informacion_dispositivo(token, app_server_url, device_id)
        
        if 'emeter' in data and 'get_realtime' in data['emeter']:
            real_time_data = data['emeter']['get_realtime']
            # Convertimos a kW y kWh
            power_value = round(real_time_data["power_mw"] / 1000.0, 2)
            power_str = "W" if power_value < 1000 else "kW"

            real_time_data_converted = {
                "current_a": round(real_time_data["current_ma"] / 1000.0, 2),  # de mA a A
                "current_a_str": "A",
                "power": power_value if power_value < 1000 else round(power_value / 1000.0, 2),  # en W o kW
                "power_str": power_str,
                "total_kwh": round(real_time_data["total_wh"] / 1000.0, 2),  # de Wh a kWh
                "total_kwh_str": "kWh",
                "voltage_v": round(real_time_data["voltage_mv"] / 1000.0, 2),  # de mV a V
                "voltage_v_str": "V",
                "err_code": real_time_data["err_code"]
            }
            return jsonify(real_time_data_converted)
        else:
            return jsonify({'error': 'Datos en tiempo real no disponibles.'}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/list_devices', methods=['GET'])
def list_devices():
    try:
        email = "rodriguezjhonatanalexander@gmail.com"
        password = "CXB4fwviF2pN$7P"
        token = get_valid_token(email, password)
        devices = listar_dispositivos(token)
        return jsonify(devices)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)