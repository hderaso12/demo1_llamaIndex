class Persona:
    def __init__(self, nombre, edad):
        self.nombre = nombre
        self.edad = edad
    
    def imprimir_informacion(self):
        print("Nombre:", self.nombre)
        print("Edad:", self.edad)


class Estudiante(Persona):
    def __init__(self, nombre, edad, grado):
        super().__init__(nombre, edad)
        self.grado = grado
    
    def imprimir_informacion(self):
        super().imprimir_informacion()
        print("Grado:", self.grado)


# Crear una instancia de la clase Estudiante
estudiante1 = Estudiante("Juan", 20, "Bachillerato")

# Imprimir los atributos del estudiante
estudiante1.imprimir_informacion()

print(Estudiante.mro())