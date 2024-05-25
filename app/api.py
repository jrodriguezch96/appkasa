from flask import Blueprint, jsonify
import pandas as pd
from .tasks import obtener_informacion_dispositivo_task, obtener_token, credentials, sheet, SPREADSHEET_ID, RANGE_NAME

api_bp = Blueprint('api', __name__)

@api_bp.route('/get_excel_data', methods=['GET'])
def get_excel_data():
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])
    df = pd.DataFrame(values, columns=['Fecha', 'Consumo'])
    return jsonify(df.to_dict(orient='records'))

@api_bp.route('/get_real_time_data', methods=['GET'])
def get_real_time_data():
    email = "rodriguezjhonatanalexander@gmail.com"
    password = "LINA210314"
    try:
        token = obtener_token(email, password)
        device_id = "8006DABB0462CC97428C72D3DA80FCBA1EC0F1A4"
        data = obtener_informacion_dispositivo_task(token, device_id)
        
        if 'emeter' in data and 'get_realtime' in data['emeter']:
            real_time_data = data['emeter']['get_realtime']
            power_value = round(real_time_data["power_mw"] / 1000.0, 2)
            power_str = "W" if power_value < 1000 else "kW"
            real_time_data_converted = {
                "current_a": round(real_time_data["current_ma"] / 1000.0, 2),
                "current_a_str": "A",
                "power": power_value if power_value < 1000 else round(power_value / 1000.0, 2),
                "power_str": power_str,
                "total_kwh": round(real_time_data["total_wh"] / 1000.0, 2),
                "total_kwh_str": "kWh",
                "voltage_v": round(real_time_data["voltage_mv"] / 1000.0, 2),
                "voltage_v_str": "V",
                "err_code": real_time_data["err_code"]
            }
            return jsonify(real_time_data_converted)
        else:
            return jsonify({'error': 'Datos en tiempo real no disponibles.'}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500