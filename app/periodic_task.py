import threading
import time
from .tasks import obtener_y_actualizar

def schedule_task():
    obtener_y_actualizar()
    # Programar la siguiente ejecución en 10 minutos (600 segundos)
    threading.Timer(600, schedule_task).start()

# Iniciar la primera ejecución
schedule_task()