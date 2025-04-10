import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import xml.etree.ElementTree as ET
from datetime import datetime
import pdfplumber
import re

# Diccionario de meses en español a número
meses_es_num = {
    "Ene": "01", "Feb": "02", "Mar": "03", "Abr": "04", "May": "05", "Jun": "06",
    "Jul": "07", "Ago": "08", "Sep": "09", "Oct": "10", "Nov": "11", "Dic": "12"
}

# Diccionario de meses en español en formato corto
meses_cortos = {
    "01": "Ene", "02": "Feb", "03": "Mar", "04": "Abr", "05": "May", "06": "Jun",
    "07": "Jul", "08": "Ago", "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dic"
}

# Función para seleccionar archivos
def seleccionar_archivos():
    global archivos_seleccionados
    archivos_seleccionados = filedialog.askopenfilenames(filetypes=[("Archivos XML y PDF", "*.xml *.pdf"), ("Archivos XML", "*.xml"), ("Archivos PDF", "*.pdf")])
    if archivos_seleccionados:
        label_archivos.config(text=f"{len(archivos_seleccionados)} archivos seleccionados")
        boton_procesar.config(state=tk.NORMAL)

# Función para pedir fecha
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

# Función para XML
def es_finiquito(root, namespaces):
    percepciones = root.findall(".//nomina12:Percepcion", namespaces)
    fecha_inicio_elem = root.find(".//nomina12:Nomina[@FechaInicialPago]", namespaces)
    fecha_fin_elem = root.find(".//nomina12:Nomina[@FechaFinalPago]", namespaces)

    claves_finiquito = {"019", "022", "024"}
    contiene_claves_finiquito = any(p.get("Clave") in claves_finiquito for p in percepciones)
    incluye_sueldo = any(p.get("Clave") == "001" and float(p.get("ImporteGravado", "0")) > 0 for p in percepciones)

    periodo_es_un_dia = False
    if fecha_inicio_elem is not None and fecha_fin_elem is not None:
        fecha_ini = fecha_inicio_elem.get("FechaInicialPago")
        fecha_fin = fecha_fin_elem.get("FechaFinalPago")
        if fecha_ini == fecha_fin:
            periodo_es_un_dia = True

    total_gravado = sum(float(p.get("ImporteGravado", "0")) for p in percepciones)
    total_exento = sum(float(p.get("ImporteExento", "0")) for p in percepciones)
    mas_exento_que_gravado = total_exento > total_gravado

    condiciones = [
        contiene_claves_finiquito,
        not incluye_sueldo,
        periodo_es_un_dia,
        mas_exento_que_gravado
    ]
    return sum(condiciones) >= 2

# Función para PDF
def es_finiquito_pdf(texto):
    condiciones = 0
    claves_finiquito = ["Vacaciones", "Prima de vacaciones", "Aguinaldo"]

    # Condición 1: Contiene conceptos típicos de finiquito
    if any(palabra in texto for palabra in claves_finiquito):
        condiciones += 1

    # Condición 2: ¿Periodo con misma fecha de inicio y fin?
    match_periodo = re.search(r"Periodo:\s.*?(\d{1,2}/\w{3}/\d{4})\s*-\s*(\d{1,2}/\w{3}/\d{4})", texto)
    if match_periodo:
        fecha_inicio, fecha_fin = match_periodo.groups()
        if fecha_inicio == fecha_fin:
            condiciones += 1

    # Condición 3: No hay concepto de sueldo como percepción
    percepciones_bloque = texto.split("Percepciones")[1].split("Deducciones")[0] if "Percepciones" in texto and "Deducciones" in texto else ""
    if "Sueldo" not in percepciones_bloque:
        condiciones += 1

    return condiciones >= 2

# Procesamiento de archivos
def procesar_archivos():
    global archivos_procesados
    archivos_procesados = []
    namespaces = {'cfdi': 'http://www.sat.gob.mx/cfd/4', 'nomina12': 'http://www.sat.gob.mx/nomina12'}
    
    fecha_deposito = solicitar_fecha()
    fecha_deposito_formateada = datetime.strptime(fecha_deposito, "%Y-%m-%d").strftime("%Y-%m-%d")

    total_finiquitos = 0
    total_recibos = 0

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
                    messagebox.showerror("Error", f"El archivo {os.path.basename(archivo)} no tiene los datos requeridos.")
                    continue
                
                curp = curp_elem.get("Curp").strip()
                fecha_inicio = datetime.strptime(fecha_inicio_elem.get("FechaInicialPago"), "%Y-%m-%d").strftime("%d")
                fecha_fin_dt = datetime.strptime(fecha_fin_elem.get("FechaFinalPago"), "%Y-%m-%d")
                fecha_fin = f"{fecha_fin_dt.strftime('%d')}{meses_cortos[fecha_fin_dt.strftime('%m')]}".lower()
                
                es_fini = es_finiquito(root, namespaces)
                tipo_documento = "14. Finiquito" if es_fini else "47. Recibos de Nómina"
                total_finiquitos += 1 if es_fini else 0
                total_recibos += 0 if es_fini else 1

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
                for mes, num in meses_es_num.items():
                    fecha_inicio = fecha_inicio.replace(mes, num)
                    fecha_fin = fecha_fin.replace(mes, num)
                
                fecha_inicio_dt = datetime.strptime(fecha_inicio, "%d/%m/%Y")
                fecha_fin_dt = datetime.strptime(fecha_fin, "%d/%m/%Y")
                fecha_inicio = fecha_inicio_dt.strftime("%d")
                fecha_fin = f"{fecha_fin_dt.strftime('%d')}{meses_cortos[fecha_fin_dt.strftime('%m')]}".lower()
                
                es_fini = es_finiquito_pdf(text)
                tipo_documento = "14. Finiquito" if es_fini else "47. Recibos de Nómina"
                total_finiquitos += 1 if es_fini else 0
                total_recibos += 0 if es_fini else 1

            else:
                messagebox.showerror("Error", f"Formato de archivo no soportado: {archivo}")
                continue

            nuevo_nombre = f"{curp}-{tipo_documento}-{fecha_inicio}al{fecha_fin}-{fecha_deposito_formateada}{extension}"
            nueva_ruta = os.path.join(os.path.dirname(archivo), nuevo_nombre)
            os.rename(archivo, nueva_ruta)
            archivos_procesados.append(nueva_ruta)

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo procesar {os.path.basename(archivo)}\n{str(e)}")

    if archivos_procesados:
        resumen = (
            f"✅ Archivos procesados correctamente:\n\n"
            f"🔸 Finiquitos: {total_finiquitos}\n"
            f"🔸 Recibos normales: {total_recibos}"
        )
        messagebox.showinfo("Resumen de procesamiento", resumen)

# GUI
root = tk.Tk()
root.title("Óptima Procesador de nombre")
root.geometry("400x300")

boton_seleccionar = tk.Button(root, text="Seleccionar Archivos", command=seleccionar_archivos)
boton_seleccionar.pack(pady=10)

label_archivos = tk.Label(root, text="No hay archivos seleccionados")
label_archivos.pack()

boton_procesar = tk.Button(root, text="Procesar Archivos", command=procesar_archivos, state=tk.DISABLED)
boton_procesar.pack(pady=10)

root.mainloop()