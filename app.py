import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import xml.etree.ElementTree as ET
from datetime import datetime
import pdfplumber

# Función para seleccionar archivos
def seleccionar_archivos():
    global archivos_seleccionados
    archivos_seleccionados = filedialog.askopenfilenames(filetypes=[("Archivos XML y PDF", "*.xml *.pdf"), ("Archivos XML", "*.xml"), ("Archivos PDF", "*.pdf")])
    if archivos_seleccionados:
        label_archivos.config(text=f"{len(archivos_seleccionados)} archivos seleccionados")
        boton_procesar.config(state=tk.NORMAL)

# Función para validar la fecha ingresada por el usuario
def solicitar_fecha():
    while True:
        fecha_deposito = simpledialog.askstring("Fecha de Depósito", "Ingrese la fecha de depósito (YYYY-MM-DD):")
        if fecha_deposito:
            try:
                datetime.strptime(fecha_deposito, "%Y-%m-%d")
                return fecha_deposito
            except ValueError:
                messagebox.showerror("Error", "Formato de fecha incorrecto. Debe ser YYYY-MM-DD.")
        else:
            messagebox.showerror("Error", "Debe ingresar una fecha de depósito válida.")

# Función para procesar archivos XML y PDF
def procesar_archivos():
    global archivos_procesados
    archivos_procesados = []
    namespaces = {'cfdi': 'http://www.sat.gob.mx/cfd/4', 'nomina12': 'http://www.sat.gob.mx/nomina12'}
    
    # Pedir fecha de depósito al usuario con validación
    fecha_deposito = solicitar_fecha()
    
    for archivo in archivos_seleccionados:
        try:
            extension = os.path.splitext(archivo)[1].lower()
            
            if extension == ".xml":
                tree = ET.parse(archivo)
                root = tree.getroot()
                
                curp_elem = root.find(".//nomina12:Receptor[@Curp]", namespaces)
                fecha_inicio_elem = root.find(".//nomina12:Nomina[@FechaInicialPago]", namespaces)
                fecha_fin_elem = root.find(".//nomina12:Nomina[@FechaFinalPago]", namespaces)
                
                if curp_elem is None or fecha_inicio_elem is None or fecha_fin_elem is None:
                    messagebox.showerror("Error", f"El archivo {os.path.basename(archivo)} no tiene los datos requeridos (Curp, FechaInicialPago o FechaFinalPago).")
                    continue
                
                curp = curp_elem.get("Curp").strip()
                fecha_inicio = fecha_inicio_elem.get("FechaInicialPago").strip()
                fecha_fin = fecha_fin_elem.get("FechaFinalPago").strip()
                
                fecha_inicio_obj = datetime.strptime(fecha_inicio, "%Y-%m-%d")
                fecha_fin_obj = datetime.strptime(fecha_fin, "%Y-%m-%d")
                fecha_inicio = fecha_inicio_obj.strftime("%d")
                fecha_fin = fecha_fin_obj.strftime("%d%b").lower()
                
            elif extension == ".pdf":
                with pdfplumber.open(archivo) as pdf:
                    text = " ".join(page.extract_text() for page in pdf.pages if page.extract_text())
                    
                curp_index = text.find("CURP:")
                periodo_index = text.find("Periodo:")
                
                if curp_index == -1 or periodo_index == -1:
                    messagebox.showerror("Error", f"No se encontraron los datos requeridos en {os.path.basename(archivo)}.")
                    continue
                
                curp = text[curp_index + 5:].split()[0].strip()
                fechas = text[periodo_index:].split("-")
                fecha_inicio = fechas[0].split()[-1].strip()
                fecha_fin = fechas[1].split()[0].strip()
                
                fecha_inicio_obj = datetime.strptime(fecha_inicio, "%d/%b/%Y")
                fecha_fin_obj = datetime.strptime(fecha_fin, "%d/%b/%Y")
                fecha_inicio = fecha_inicio_obj.strftime("%d")
                fecha_fin = fecha_fin_obj.strftime("%d%b").lower()
                
            else:
                messagebox.showerror("Error", f"Formato de archivo no soportado: {archivo}")
                continue
            
            nuevo_nombre = f"{curp}-47. Recibos de Nómina-{fecha_inicio}al{fecha_fin}-{fecha_deposito}{extension}"
            nueva_ruta = os.path.join(os.path.dirname(archivo), nuevo_nombre)
            os.rename(archivo, nueva_ruta)
            archivos_procesados.append(nueva_ruta)
        
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo procesar {os.path.basename(archivo)}\n{str(e)}")
    
    if archivos_procesados:
        messagebox.showinfo("Éxito", "Archivos procesados correctamente")

# Configuración de la ventana principal
root = tk.Tk()
root.title("Procesador de XML y PDF")
root.geometry("400x300")

# Botón para seleccionar archivos
boton_seleccionar = tk.Button(root, text="Seleccionar Archivos", command=seleccionar_archivos)
boton_seleccionar.pack(pady=10)

# Etiqueta para mostrar la cantidad de archivos seleccionados
label_archivos = tk.Label(root, text="No hay archivos seleccionados")
label_archivos.pack()

# Botón para procesar archivos
boton_procesar = tk.Button(root, text="Procesar Archivos", command=procesar_archivos, state=tk.DISABLED)
boton_procesar.pack(pady=10)

# Ejecutar la aplicación
root.mainloop()