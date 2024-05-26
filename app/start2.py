import requests
import json
import uuid
from datetime import datetime, timedelta
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import schedule
import time
import numpy as np
import threading
import sys

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

datesOmmited = [
    '2024-04-25',
    '2024-05-06',
    '2024-05-07',
    '2024-05-08',
    '2024-05-09',
    '2024-05-10',
    '2024-05-23',
    '2024-05-24'
]

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
        print("response obtener_token...", response.json(), flush=True)
        data = response.json()
        print("data obtener_token...", data, flush=True)
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

def obtener_informacion_dispositivo(token, device_id, year, month, retries=3, delay=60):
    url = f"https://wap.tplinkcloud.com?token={token}"
    payload = {
        "method": "passthrough",
        "params": {
            "deviceId": device_id,
            "requestData": json.dumps({
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
    for attempt in range(retries):
        response = requests.post(url, json=payload)
        # print("response obtener_informacion_dispositivo...", response.json(), flush=True)
        print("Obteniendo información del dispositivo...", response, flush=True)
        data = response.json()
        print("data obtener_informacion_dispositivo...", data, flush=True)
        consumo = json.loads(data['result']['responseData'])
        return consumo
    raise Exception("Número máximo de intentos excedido. Por favor, inténtelo de nuevo más tarde.")

def leer_datos():
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])
    if not values:
        return pd.DataFrame(columns=['Fecha', 'Consumo (kWh)'])
    else:
        df = pd.DataFrame(values[1:], columns=values[0])
        df['Consumo (kWh)'] = df['Consumo (kWh)'].str.replace(',', '.').astype(float)
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce').dt.strftime('%Y-%m-%d')
        if df['Fecha'].isnull().any():
            print("Error al convertir algunas fechas. Verifica los datos en la hoja de cálculo.", flush=True)
        df = df.dropna(subset=['Fecha'])
        return df

def escribir_datos(df):
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    if df['Fecha'].isnull().any():
        print("Error al convertir algunas fechas. Verifica los datos en la hoja de cálculo.", flush=True)
    df = df.dropna(subset=['Fecha'])
    df['Fecha'] = df['Fecha'].dt.strftime('%Y-%m-%d')
    values = [df.columns.tolist()] + df.values.tolist()
    body = {
        'values': values
    }
    result = sheet.values().update(
        spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME,
        valueInputOption='RAW', body=body).execute()

def actualizar_consumo(consumption_data):
    df = leer_datos()
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    if df['Fecha'].isnull().any():
        print("Error al convertir algunas fechas. Verifica los datos en la hoja de cálculo.", flush=True)
    df = df.dropna(subset=['Fecha'])
    new_rows = []
    for day_stat in consumption_data:
        date_str = f"{day_stat['year']}-{day_stat['month']:02d}-{day_stat['day']:02d}"
        date = np.datetime64(date_str)
        energy_wh = day_stat['energy_wh']
        energy_kwh = energy_wh / 1000
        if date_str in datesOmmited:
            continue
        if str(date) in df['Fecha'].astype(str).values:
            current_consumption = df.loc[df['Fecha'].dt.date == date, 'Consumo (kWh)'].values[0]
            # print(f"Consumo actual: {current_consumption}, Consumo nuevo: {energy_kwh}", flush=True)
            if current_consumption != energy_kwh:
                df.loc[df['Fecha'].dt.date == date, 'Consumo (kWh)'] = energy_kwh
        else:
            new_rows.append({'Fecha': date, 'Consumo (kWh)': energy_kwh})
    
    if new_rows:
        new_df = pd.DataFrame(new_rows)
        df = pd.concat([df, new_df], ignore_index=True)

    if not df['Fecha'].isnull().values.any():
        df.sort_values('Fecha', inplace=True)
    else:
        print("No se pueden ordenar las fechas debido a valores nulos.", flush=True)
    escribir_datos(df)

def obtener_rango_fechas(token, device_id, start_date, end_date):
    current_date = start_date
    consumption_data = []

    while current_date <= end_date:
        year = current_date.year
        month = current_date.month
        infoEnchufe = obtener_informacion_dispositivo(token, device_id, year, month)
        print(f"Obteniendo datos para {year}-{month:02d}...", flush=True)
        if 'emeter' in infoEnchufe and 'get_daystat' in infoEnchufe['emeter']:
            day_stats = infoEnchufe['emeter']['get_daystat']['day_list']
            for day_stat in day_stats:
                stat_date = datetime(year=day_stat['year'], month=day_stat['month'], day=day_stat['day'])
                if start_date <= stat_date <= end_date:
                    consumption_data.append(day_stat)
        current_date = datetime(year=year + (month // 12), month=(month % 12) + 1, day=1)    
    return consumption_data

def obtener_y_actualizar():
    try:
        email = "rodriguezjhonatanalexander@gmail.com"
        password = "CXB4fwviF2pN$7P"
        token = get_valid_token(email, password)
        
        # Fecha de hoy
        end_date = datetime.now()
        # Fecha de 30 días atrás
        start_date = end_date - timedelta(days=30)
        print(f"Obteniendo datos de consumo desde {start_date} hasta {end_date}...", flush=True)
        consumption_data = obtener_rango_fechas(token, "8006DABB0462CC97428C72D3DA80FCBA1EC0F1A4", start_date, end_date)
        actualizar_consumo(consumption_data)
        print("Datos actualizados en Google Sheets.", flush=True)
    except Exception as e:
        print(f"Error al obtener o actualizar datos: {e}", flush=True)

def schedule_task():
    print("Inicio de la tarea programada...", flush=True)
    try:
        obtener_y_actualizar()
        # Programar la siguiente ejecución en 10 minutos (600 segundos)
        threading.Timer(600, schedule_task).start()
    except KeyboardInterrupt:
        print("Programa interrumpido por el usuario. Saliendo...")
        sys.exit()

# Iniciar la primera ejecución
schedule_task()