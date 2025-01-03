import requests
from requests.auth import HTTPBasicAuth

# Credenciales de acceso
username = 'qasupport'  # Reemplaza con tu usuario de Confluence
password = 'temporal'  # Reemplaza con tu contraseña

# ID de la página
page_id = '327484345'

# URL de la API de Confluence
url = f'https://confluence.tid.es/rest/api/content/{page_id}'

# Realizar la solicitud GET
response = requests.get(url, auth=HTTPBasicAuth(username, password))

# Verificar si la solicitud fue exitosa
if response.status_code == 200:
    page_data = response.json()  # Convertir la respuesta a JSON
    space_key = page_data['space']['key']  # Obtener el spaceKey
    title = page_data['title']  # Obtener el title
    
    # Imprimir los resultados
    print(f'Space Key: {space_key}')
    print(f'Title: {title}')
else:
    print(f'Error al obtener la página: {response.status_code} - {response.text}')