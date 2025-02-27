import requests
import base64
import json
# gitignore

# Configurações da API
API_KEY = f""
URL = f"https://api.sieg.com/BaixarXmlsV2?api_key="

# Parâmetros da requisição JSON
payload = {
    "XmlType": 1,  # 1 = NFe
    "Take": 50,  # Máximo 50 XMLs por requisição
    "Skip": 0,
    "DataEmissaoInicio": "2025-02-25",
    "DataEmissaoFim": "2025-02-25",
    "CnpjEmit": "09240049000196",
    "Downloadevent": False
}

# Cabeçalhos da requisição
headers = {"Content-Type": "application/json"}


# Enviar requisição POST
response = requests.post(URL, headers=headers, json=payload)

# Verificar se a resposta foi bem-sucedida
if response.status_code == 200:
    print("🔹 Resposta JSON da API:")
    print(response.text)  # ADICIONADO para ver a resposta real no Python

    try:
        data = response.json()

        print("🔹 Resposta JSON bruta:", data)

        # Transformar a string JSON em array real
        if isinstance(data, str):
            data = json.loads(data)  # Converter string JSON para um dicionário real

        # Verificar se há XMLs na resposta
        if isinstance(data, list) and len(data) > 0:
            for i, xml_base64 in enumerate(data, 1):
                xml_content = base64.b64decode(xml_base64).decode("utf-8")

                # Criar e salvar arquivo XML
                file_name = f"xml_nota_{i}.xml"
                with open(file_name, "w", encoding="utf-8") as file:
                    file.write(xml_content)

                print(f"✅ XML {i} salvo: {file_name}")

        else:
            print("⚠️ Nenhum XML retornado pela API.")

    except json.JSONDecodeError:
        print("❌ Erro ao decodificar a resposta JSON.")

else:
    print(f"❌ Erro na requisição: {response.status_code} - {response.text}")