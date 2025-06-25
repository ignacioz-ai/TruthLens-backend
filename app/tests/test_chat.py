import requests
import json
from app.core.config import settings

API_URL = f"{settings.TEST_API_BASE_URL}/api/v1/chat"
headers = {"Content-Type": "application/json"}

# Test case 1: Verificar una noticia
test_case_1 = {
    "messages": [
        {
            "role": "user",
            "content": "Analicemos la veracidad de esta noticia: 'El gobierno anunció que la inflación bajó al 2% en el último mes'"
        }
    ],
    "use_web_search": True
}

# Test case 2: Pregunta general
test_case_2 = {
    "messages": [
        {
            "role": "user",
            "content": "¿Cuál es la última noticia sobre el cambio climático?"
        }
    ],
    "use_web_search": True
}

def test_chat(payload):
    print("\nEnviando petición...")
    print(f"Mensaje: {payload['messages'][0]['content']}")
    print(f"Web search: {payload['use_web_search']}")
    
    response = requests.post(API_URL, json=payload, headers=headers)
    
    print("\nRespuesta:")
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("✅ Response OK")
        print("\nContenido de la respuesta:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    else:
        print("❌ Error en la respuesta:")
        print(response.text)

if __name__ == "__main__":
    print("=== Test Case 1: Verificación de noticia ===")
    test_chat(test_case_1)
    
    print("\n=== Test Case 2: Pregunta general ===")
    test_chat(test_case_2) 