import random

def generar_secuencia(longitud):
    return [random.randint(0, 9) for _ in range(longitud+10)]

def prueba_memoria(secuencia):
    correctas = 0
    incorrectas = 0
    for i in range(2, len(secuencia)):
        print("Número actual:", secuencia[i])
        respuesta = input("Presiona 'f' si es diferente al número dos lugares atrás, 'j' si es el mismo número: ")
        
        numero_dos_atras = secuencia[i - 2]
        numero_un_atras = secuencia[i - 1]
        
        if respuesta == 'f' and secuencia[i] != numero_dos_atras:
            print("Respuesta correcta.")
            correctas += 1
        elif respuesta == 'j' and (secuencia[i] == numero_dos_atras or secuencia[i] == numero_un_atras):
            print("Respuesta correcta.")
            correctas += 1
        else:
            print("Respuesta incorrecta.")
            incorrectas += 1
    
    print("\nTotal de respuestas correctas:", correctas)
    print("Total de respuestas incorrectas:", incorrectas)

# Generar una secuencia aleatoria de longitud 10
secuencia = generar_secuencia(10)
print("Secuencia generada:", secuencia)

# Realizar la prueba de memoria
print("\nComienza la prueba de memoria:")
prueba_memoria(secuencia)
