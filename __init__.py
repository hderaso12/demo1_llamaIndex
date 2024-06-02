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
import pandas as pd
import re

#funcion para leer llaves necesarias y tokens
def leer_credenciales(nombre_archivo):
    credenciales = {}
    with open(nombre_archivo, "r") as file:
        for line in file:
            line = line.strip()
            if not line or ": " not in line:
                continue  # Ignorar líneas vacías o sin delimitador ": "
            key, value = line.split(": ", 1)  # Asegurar que solo se divida en 2 partes
            credenciales[key] = value.strip('"')
    return credenciales


credenciales = leer_credenciales("credenciales.txt")
api_key = credenciales.get("openai_api_key")
client = OpenAI(api_key=api_key)
os.environ["OPENAI_API_KEY"] = api_key

# Lee el archivo Excel
excel_clientes = 'numero_cliente.xlsx'
df = pd.read_excel(excel_clientes)
#datos_url = pd.read_excel('numero_cliente.xlsx', sheet_name='bd_clientes')

app = Flask(__name__)
###################################################################

def carga_llamaindex():
    # Esta función inicializa o carga un índice Jina desde un directorio persistente

    PERSIST_DIR = "./storage11"

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
        
    memory = ChatMemoryBuffer.from_defaults(token_limit=2800)
    # En cualquier caso, ahora podemos consultar el índice
    chat_engine = index.as_chat_engine(
        chat_mode="context",
        memory=memory,
        system_prompt=(
            #"Eres un chatbot, capaz de tener interacciones normales, donde respondas a la pregunta solicitada y menciones si falta algun campo"
            
            #"Eres un chatbot, capaz de tener interacciones normales para reconocer campos necesarios, identifica si te hace falta información para responder la pregunta y contestar preguntando los campos faltantes en el campo mensaje para complementar, Si tienes toda la estructura de información necesaria, contesta la pregunta"),)

            "Eres un chatbot diseñado para mantener conversaciones naturales y responder preguntas de temas de soporte de consultas a bases de datos y servidores, si recibe preguntas fuera de este contexto enviar un mensaje de que no se puede realizar esa solicitud. Debes reconocer automáticamente los campos necesarios y obligatorios teniendo en cuenta que como primer parametro se tiene cliente: {nombre_cliente}, para formar el JSON de respuesta, en los mensajes suministrados por el usuario se debe identificar si falta información para realizar la pregunta de ese campo faltante y mantener la informacion que se reconocio, para obtener la respuesta JSON y la cual debe proporcionar una estructura completa. Si la pregunta está completa, debes responder directamente la estructura JSON mencionada. Si falta información, debes solicitarla de manera clara y precisa al usuario para completarla correctamente la solicitud sin dejar NINGUN campo vacio"),)
    
            # "Eres un chatbot, capaz de tener interacciones normales para reconocer campos necesarios para crear la respuesta solo sea estructura deseada json sumando a la respuesta la variable que se llama cliente: {nombre_cliente}, identifica si te hace falta información para responder la pregunta y contestar preguntando los campos faltantes en el mensaje a complementar, Si tienes toda la información necesaria, contesta la pregunta incluiré el campo 'cliente' con el valor '" + nombre_cliente + "'."),)
    return chat_engine

# Variables para almacenar datos de la consulta
chat_engine = carga_llamaindex()
print("carga LlamaIndex")
telefono_cliente_error = None

@app.route("/webhook/", methods=["POST", "GET"])
def webhook_whatsapp():

    if request.method == "GET":
        token_conexion = credenciales.get("token_conexion")
        print(token_conexion)
        if request.args.get('hub.verify_token') == credenciales.get("token_conexion"):           
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
        idWA = message_info['id']
        timestamp = message_info['timestamp']
        print("llega solicitud por WhatsApp")
        print(mensaje)                     

        numero = int(telefono_cliente)
        # Filtra el DataFrame para encontrar el cliente correspondiente al número ingresado
        cliente = df.loc[df['numero'] == numero, 'cliente'].values
        # Verifica si se encontró algún cliente
        if len(cliente) > 0:
            print("***********=======================> El cliente correspondiente al número", numero, "es:", cliente[0])
            nombre_cliente = cliente[0]
            
            ###################
            ##url_cliente = obtener_url(nombre_cliente, excel_clientes)

            # if url_cliente:
            #     print(f"La URL para el cliente {numero}: {url_cliente}")
            # else:
            #     print(f"No se encontró la URL para el cliente con número {cliente}.")
            #    ### aqui debe reiniciar chatbot::::::::::
                     
            informacion_ingresada = mensaje
            if informacion_ingresada.lower() == 'salir':
                print("Saliendo del programa.")
                response = "saliendo de la consulta"
                enviar_respuesta(telefono_cliente,  (response))
                chat_engine.reset()
                mensaje = ""
            else:   
                response = str(chat_engine.chat(informacion_ingresada + nombre_cliente))
                #print(response)
                print(type(response))
                #funcion para seleccionar estructura json
                response = extraer_json(response)
                try:
                    
                    print("ingreso a funcion de extraccion json:::::::::::::::::::::::::::::::::::::::::::::")
                    response_json = json.loads(response)
                    #response_json["cliente"] = nombre_cliente
                    print((response_json))
                    if "mensaje" in response_json:
                        diccionario_estructura_consulta = (response_json)
                        #campos_solicitud(diccionario_estructura_consulta, telefono_cliente, url_cliente)
                        campos_solicitud(diccionario_estructura_consulta, telefono_cliente)
                        print("Estructura generada para enviar a funcion de consulta de servicio")
                        response = "."
                except json.JSONDecodeError:
                    print("La respuesta no es un JSON válido")
                enviar_respuesta(telefono_cliente, (response))
            
        else:
            response = "No se encontró ningún cliente para el número: " + str(numero)
            enviar_respuesta(telefono_cliente, (response))

    # except ValueError as e:
    #     print(f"Error: Debes ingresar números válidos. Se produjo un error: {e}")
    #     # Datos de depuración
    #     print(f"Tipo de excepción: {type(e).__name__}")
    #     print(f"Argumentos de la excepción: {e.args}")
       
    except Exception as e:
        print("--- Error al procesar el mensaje ---")
        #print(f'excepcion numero::: {numero}')
        respuesta = str(e)
        print(respuesta)
        #enviar_respuesta(telefono_cliente_error, respuesta)
        # chat_engine.reset()
        
#aqui se define el envio de estructura para que realice tarea de consulta a servicio 
#def campos_solicitud(diccionario_estructura_consulta, telefono_cliente, url_cliente):
def campos_solicitud(diccionario_estructura_consulta, telefono_cliente):    
    try:
        response = diccionario_estructura_consulta["mensaje"]
        enviar_respuesta(telefono_cliente, (response))
        print("----------> Enviar consulta java")
        print(diccionario_estructura_consulta)
        serv_nombre = diccionario_estructura_consulta['lugar']
        accion_requerida = diccionario_estructura_consulta['accion']
        opcional =  diccionario_estructura_consulta['opcional']
        nombre_cliente =  diccionario_estructura_consulta['cliente']
        
        url_cliente =  diccionario_estructura_consulta['url']       
        url = url_cliente
        data = {
            "srvName": serv_nombre,
            "qryAction": accion_requerida,
            "opcional": opcional,
            "cliente" : nombre_cliente
        }
        print(data)
        respuesta = respuesta_api_request(url, data)
        print(f'respuesta de servicio java + {respuesta}')
        print(type(respuesta))
        enviar_respuesta(telefono_cliente, str(respuesta))
        chat_engine.reset()
        
    except Exception as e:
        print("--- Error al procesar la petición ---")
        print(str(e))
        respuesta = "no se encuentra respuesta de la consulta con la informacion suministrada"
        enviar_respuesta(telefono_cliente, str(respuesta))
     
def enviar_respuesta(telefonoRecibe, respuesta):
    # ... (tu código para enviar respuesta por WhatsApp)
    from heyoo import WhatsApp
  #TOKEN DE ACCESO DE FACEBOOK
    token=credenciales.get("facebook_token")
    #IDENTIFICADOR DE NÚMERO DE TELÉFONO
    idNumeroTeléfono=credenciales.get("numero_celular")
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
              
                consulta = lineas[0].strip() if lineas and lineas[0].strip().isdigit() else None
                mensaje = lineas[1].strip() if len(lineas) > 1 else None
                # Crear estructura JSON
                estructura_json = {
                    "mensaje_adicional": mensaje,
                    "consulta": consulta                    
                }
                # Convertir a JSON sin escapar caracteres no ASCII
                json_resultado = json.dumps(estructura_json, ensure_ascii=False)
                resultado_estructura= mensaje + " "+ consulta
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
        return "se genero un error con los datos obtenidos, se revisara la información para dar solucion"
    
def extraer_json(response):
    # Buscar la línea que contiene la palabra "json"
    match = re.search(r'json\s*({.*?})', response, re.DOTALL)
    if match:
        # Extraer la estructura JSON
        json_part = match.group(1)
        print("Parte JSON encontrada:")
        return json_part
    else:
        print("No se encontró ninguna estructura JSON en la cadena.")
        return response


def obtener_url(cliente, archivo_excel):
    try:
        datos = pd.read_excel(archivo_excel, sheet_name='bd_clientes')
        url_cliente = datos.loc[datos['cliente'] == cliente, 'links'].values
        if len(url_cliente) > 0:
            return url_cliente[0]
        else:
            return "Cliente no coincide con la base de datos"
    except (FileNotFoundError, IndexError):
        return "Error al procesar el archivo"


if __name__ == "__main__":
    app.run(debug=True)




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