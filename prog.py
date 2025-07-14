import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from openpyxl import Workbook, load_workbook
import threading
import os
import time

# === CONFIGURAÇÕES ===
USANDO_GPIO = False
try:
    import RPi.GPIO as GPIO
    USANDO_GPIO = True
except ImportError:
    class GPIOFake:
        BCM = 'BCM'
        IN = 'IN'
        PUD_DOWN = 'PUD_DOWN'
        def setmode(self, mode): pass
        def setup(self, pin, mode, pull_up_down=None): pass
        def input(self, pin): return False
        def cleanup(self): pass
    GPIO = GPIOFake()

SENSOR_LARGADA = 17  # GPIO17
SENSOR_CHEGADA = 27  # GPIO27
ARQUIVO_EXCEL = 'leituras.xlsx'

# === GPIO SETUP ===
GPIO.setmode(GPIO.BCM)
GPIO.setup(SENSOR_LARGADA, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(SENSOR_CHEGADA, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# === DADOS ===
leituras = []
medindo = False
thread_leitura = None

# === EXCEL ===
def salvar_leitura_excel(leitura):
    if not os.path.exists(ARQUIVO_EXCEL):
        wb = Workbook()
        ws = wb.active
        ws.append(['Data', 'Hora', 'Passagem', 'Tempo (s)'])
    else:
        wb = load_workbook(ARQUIVO_EXCEL)
        ws = wb.active

    numero_passagem = len(ws['A'])
    data = leitura['data']
    hora = leitura['hora']
    tempo = leitura['tempo']
    ws.append([data, hora, numero_passagem, tempo])
    wb.save(ARQUIVO_EXCEL)

# === GUI ===
root = tk.Tk()
root.title("Cronometragem")
root.geometry("480x320")
root.configure(bg='white')

frame_lista = tk.Frame(root, bg='white')
frame_lista.place(x=0, y=0, width=240, height=320)

lista = tk.Listbox(frame_lista, font=("Arial", 14), selectmode=tk.SINGLE)
lista.pack(fill=tk.BOTH, expand=True)

frame_controles = tk.Frame(root, bg='white')
frame_controles.place(x=240, y=0, width=240, height=320)

btn_iniciar = tk.Button(frame_controles, text="INICIAR", bg='lightcoral', font=("Arial", 14), width=10)
btn_iniciar.pack(pady=10)

btn_excluir = tk.Button(frame_controles, text="EXCLUIR", bg='red', fg='white', font=("Arial", 10))
btn_excluir.pack(pady=5)

lbl_largada = tk.Label(frame_controles, text="LARGADA", font=("Arial", 10))
lbl_largada.pack()
canvas_largada = tk.Canvas(frame_controles, width=50, height=50)
circ_largada = canvas_largada.create_oval(5, 5, 45, 45, fill='darkgreen')
canvas_largada.pack()

lbl_chegada = tk.Label(frame_controles, text="CHEGADA", font=("Arial", 10))
lbl_chegada.pack()
canvas_chegada = tk.Canvas(frame_controles, width=50, height=50)
circ_chegada = canvas_chegada.create_oval(5, 5, 45, 45, fill='darkgreen')
canvas_chegada.pack()

# === FUNÇÕES ===
def atualizar_circulo(sensor_id, ativo):
    cor = 'lime' if ativo else 'darkgreen'
    if sensor_id == SENSOR_LARGADA:
        canvas_largada.itemconfig(circ_largada, fill=cor)
    elif sensor_id == SENSOR_CHEGADA:
        canvas_chegada.itemconfig(circ_chegada, fill=cor)

def monitorar():
    global medindo
    btn_iniciar.config(text="LENDO", bg='green')
    while medindo:
        if GPIO.input(SENSOR_LARGADA):
            atualizar_circulo(SENSOR_LARGADA, True)
            t1 = time.time()
            while GPIO.input(SENSOR_LARGADA):
                time.sleep(0.01)  # espera desligar
            time.sleep(0.3)  # ignora o segundo sinal

            while not GPIO.input(SENSOR_CHEGADA):
                if not medindo:
                    return
                time.sleep(0.01)

            atualizar_circulo(SENSOR_CHEGADA, True)
            t2 = time.time()
            tempo = round(t2 - t1, 2)
            dt = datetime.now()
            leitura = {
                'data': dt.strftime('%d/%m/%Y'),
                'hora': dt.strftime('%H:%M:%S'),
                'tempo': tempo
            }
            leituras.append(leitura)
            salvar_leitura_excel(leitura)
            atualizar_lista()
            break
        time.sleep(0.05)
    btn_iniciar.config(text="INICIAR", bg='lightcoral')
    atualizar_circulo(SENSOR_LARGADA, False)
    atualizar_circulo(SENSOR_CHEGADA, False)

def atualizar_lista():
    lista.delete(0, tk.END)
    for i, l in enumerate(leituras, start=1):
        lista.insert(tk.END, f"{i:02} - {l['tempo']}s")

def iniciar_parar():
    global medindo, thread_leitura
    if not medindo:
        medindo = True
        thread_leitura = threading.Thread(target=monitorar)
        thread_leitura.start()
    else:
        medindo = False

def excluir_leitura():
    sel = lista.curselection()
    if not sel:
        return
    idx = sel[0]
    leituras.pop(idx)
    atualizar_lista()

btn_iniciar.config(command=iniciar_parar)
btn_excluir.config(command=excluir_leitura)

# === LOOP ===
try:
    root.mainloop()
finally:
    GPIO.cleanup()