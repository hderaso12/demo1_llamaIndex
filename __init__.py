from flask import Flask, jsonify, request
#import openai
import requests
from openai import OpenAI
from heyoo import WhatsApp
import json
import difflib
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    load_index_from_storage,
)
from llama_index.core.memory import ChatMemoryBuffer
import os

api_key = "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"

client = OpenAI(api_key=api_key)
os.environ["OPENAI_API_KEY"] = api_key

import pandas as pd

# Lee el archivo Excel
df = pd.read_excel('numero_cliente.xlsx')

app = Flask(__name__)
###################################################################

def carga_llamaindex():
    # Esta función inicializa o carga un índice Jina desde un directorio persistente

    PERSIST_DIR = "./storage7"

    if not os.path.exists(PERSIST_DIR):
        # Cargar los documentos y crear el índice
        documents = SimpleDirectoryReader(input_dir="./data").load_data()
        index = VectorStoreIndex.from_documents(documents)
        # Almacenarlo para más tarde
        index.storage_context.persist(persist_dir=PERSIST_DIR)
    else:
        # Cargar el índice existente
        storage_context = StorageContext.from_defaults(persist_dir=PERSIST_DIR)
        index = load_index_from_storage(storage_context)
        
    memory = ChatMemoryBuffer.from_defaults(token_limit=1000)
    # En cualquier caso, ahora podemos consultar el índice
    chat_engine = index.as_chat_engine(
        chat_mode="context",
        memory=memory,
        system_prompt=(
            #"Eres un chatbot, capaz de tener interacciones normales, donde respondas a la pregunta solicitada y menciones si falta algun campo"
            "Eres un chatbot, capaz de tener interacciones normales para reconocer campos necesarios, identifica si te hace falta información para responder la pregunta y contestar preguntando los campos faltantes en el campo mensaje para complementar, Si tienes toda la información necesaria, contesta la pregunta"),)
    return chat_engine

# Variables para almacenar datos de la consulta
chat_engine = carga_llamaindex()
print("carga LlamaIndex")

@app.route("/webhook/", methods=["POST", "GET"])
def webhook_whatsapp():

    if request.method == "GET":
        if request.args.get('hub.verify_token') == "Token2023":           
            return request.args.get('hub.challenge')
        else:
            return "Error de autenticación."

    if request.method == "POST":
        data = request.get_json()
        handle_whatsapp_message(data)
    return jsonify({"status": "success"}), 200

def handle_whatsapp_message(data):

    try:
        message_info = data['entry'][0]['changes'][0]['value']['messages'][0]
        telefono_cliente = message_info['from']
        print(telefono_cliente)
        mensaje = message_info['text']['body']
        mensaje_global = mensaje
        idWA = message_info['id']
        timestamp = message_info['timestamp']
        print("llega solicitud por WhatsApp")
        print(mensaje)                     

        numero = int(telefono_cliente)
        # Filtra el DataFrame para encontrar el cliente correspondiente al número ingresado
        cliente = df.loc[df['numero'] == numero, 'cliente'].values

        # Verifica si se encontró algún cliente
        if len(cliente) > 0:
            print("**************El cliente correspondiente al número", numero, "es:", cliente[0])
            nombre_cliente = cliente[0]
            print(nombre_cliente)
            if ("Hola") in mensaje:
                enviar_respuesta(telefono_cliente, "Hola, ¿cómo puedo ayudarte?")
        
            else:
                
                informacion_ingresada = mensaje

                if informacion_ingresada.lower() == 'salir':
                    print("Saliendo del programa.")
                    response = "saliendo de la consulta"
                    enviar_respuesta(telefono_cliente,  (response))
                    chat_engine.reset()
                    mensaje = ""
                else:   
                    response = str(chat_engine.chat(informacion_ingresada))
                    print(response)
                    print(type(response))
                    try:
                        response_json = json.loads(response)
                        if "mensaje" in response_json:
                            diccionario_estructura_consulta = (response_json)
                            #campos_solicitud(diccionario_estructura_consulta, telefono_cliente)
                            print("Estructura generada para enviar a funcion de consulta de servicio")
                            #response = "."
                    except json.JSONDecodeError:
                        print("La respuesta no es un JSON válido")

                    enviar_respuesta(telefono_cliente, (response))
            
        else:
            response = "No se encontró ningún cliente para el número: " + str(numero)
            enviar_respuesta(telefono_cliente, (response))
       

    except Exception as e:
        print("--- Error al procesar el mensaje ---")
        print(str(e))
        
#aqui se define el envio de estructura para que realice tarea de consulta a servicio 
def campos_solicitud(diccionario_estructura_consulta, telefono_cliente):
    try:
        response = diccionario_estructura_consulta["mensaje"]
        enviar_respuesta(telefono_cliente, (response))
        print("----------> Enviar consulta a Angie")
        print(diccionario_estructura_consulta)
        serv_nombre = diccionario_estructura_consulta['lugar']
        accion_requerida = diccionario_estructura_consulta['accion']
        #mas_informacion =  diccionario_estructura_consulta['']
        url_peticion =    "http://192.168.169.23:8083/dbaexperts/dataBase"             
        url = url_peticion
        data = {
            "srvName": serv_nombre,
            "qryAction": accion_requerida,
            "valores": []
        }
        print(data)
        respuesta = respuesta_api_request(url, data)
        enviar_respuesta(telefono_cliente, respuesta)
        chat_engine.reset()
        
    except Exception as e:
        print("--- Error al procesar la petición ---")
        print(str(e))
 
    
# def reset_variables():
#     global host, usuario, contrasena, base_datos, isHost, isUsuario, isContrasena, isBaseDatos, isMensajeGlobal, mensaje_global
#     host = ""
#     usuario = ""
#     contrasena = ""
#     base_datos = ""
#     isHost = False
#     isUsuario = False
#     isContrasena = False
#     isBaseDatos = False
#     isMensajeGlobal = False
#     mensaje_global = ""

# def generate_response(mensaje):
#     model_engine = "text-davinci-003"
#     completion = client.completions.create(
#         model=model_engine,
#         prompt=mensaje,
#         max_tokens=64,
#         n=1,
#         stop=None,
#         temperature=0.01
#     )
#     respuesta = "".join(choice.text for choice in completion.choices)
#     respuesta = respuesta.replace("\\n", "\\\n").replace("\\", "")
#     print("respuesta de api OpenAi")
#     return respuesta

def enviar_respuesta(telefonoRecibe, respuesta):
    # ... (tu código para enviar respuesta por WhatsApp)
    from heyoo import WhatsApp
  #TOKEN DE ACCESO DE FACEBOOK
    token='EAALZBPNmy0FgBO6T8sdssZBoYUYg9R9v7HhesctA99whQ5ydixh7hxwwXfMEXCcA3F20ghqFIZBmdcuHlkFbtjoQFxaUxZCMmstahB2wnL6UOHcGvGgUyCOkw9yhud4FRZCNJ2tVRRZCurEbZCXZCDhloTiQrrVUIOzcgZChZBcm54CBxu8UZABhKA8d4rolYtAGjQT3R6eV09gLFv9L71avCt6'
    #IDENTIFICADOR DE NÚMERO DE TELÉFONO
    idNumeroTeléfono='118462694689557'
    #INICIALIZAMOS ENVIO DE MENSAJES
    mensajeWa=WhatsApp(token,idNumeroTeléfono)
    telefonoRecibe=telefonoRecibe.replace("521","57")
    #ENVIAMOS UN MENSAJE DE TEXTO
    mensajeWa.send_message(respuesta,telefonoRecibe)
    
def respuesta_api_request(url, data):
    try:
        # Realiza la solicitud POST con los datos
        response = requests.post(url, json=data)
        # Verifica si la solicitud fue exitosa (código de estado 200)
        if response.status_code == 200:
            
        # Imprime la respuesta completa del servidor
            respuesta_texto = response.text.strip()  # Eliminar espacios en blanco al principio y al final

            # Intenta procesar la respuesta en formato JSON
            try:
                # Divide el texto en líneas
                lineas = respuesta_texto.split('\n')
                print(lineas)
                # Obtener el número de sesiones y el mensaje
                num_sesiones = lineas[0].strip() if lineas and lineas[0].strip().isdigit() else None
                mensaje = lineas[1].strip() if len(lineas) > 1 else None

                # Crear estructura JSON
                estructura_json = {
                    "mensaje_adicional": mensaje,
                    "num_sesiones": num_sesiones                    
                }

                # Convertir a JSON sin escapar caracteres no ASCII
                json_resultado = json.dumps(estructura_json, ensure_ascii=False)
                resultado_estructura= mensaje + " "+ num_sesiones
                # Imprimir el resultado
                print("resultado respuesta de consumo microservicio")
                print(json_resultado)
                return resultado_estructura
            except ValueError as ve:
                print(f"Error al procesar la respuesta con JSON en microservicio: {ve}")
                
        else:
            print(f"Error en microservicio: {response.status_code}")
            entrega_respuesta = "No se pudo obtener respuesta del microservicio"
            return entrega_respuesta
    except requests.RequestException as e:
        print(f"Error de conexión: {e}")
    

if __name__ == "__main__":
    app.run(debug=True)

        