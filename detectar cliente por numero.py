import pandas as pd

# Lee el archivo Excel
df = pd.read_excel('numero_cliente.xlsx')

# Solicita al usuario que ingrese un número
numero = input("Ingresa un número: ")

# Convierte el número ingresado a tipo int
numero = int(numero)

# Filtra el DataFrame para encontrar el cliente correspondiente al número ingresado
cliente = df.loc[df['numero'] == numero, 'cliente'].values

# Verifica si se encontró algún cliente
if len(cliente) > 0:
    print("El cliente correspondiente al número", numero, "es:", cliente[0])
    nombre_cliente = cliente[0]
else:
    print("No se encontró ningún cliente para el número", numero)
