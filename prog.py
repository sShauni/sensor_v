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

SENSOR_LARGADA = 17
SENSOR_CHEGADA = 27
PASTA_LOGS = 'logs'
log_index = 0
ARQUIVO_EXCEL = ''
lista_logs = []
log_atual = ''
leituras = []
medindo = False
thread_leitura = None

# === FUNÇÕES DE LOG ===
def listar_logs_existentes():
    global lista_logs
    if not os.path.exists(PASTA_LOGS):
        os.makedirs(PASTA_LOGS)
    lista_logs = sorted([f[:-5] for f in os.listdir(PASTA_LOGS) if f.endswith('.xlsx')])

def criar_novo_log():
    global ARQUIVO_EXCEL, leituras, log_atual, log_index
    hoje = datetime.now().strftime('%d%m%y')
    listar_logs_existentes()
    existentes = [f for f in lista_logs if f.startswith(hoje)]
    novo_nome = hoje if not existentes else f"{hoje}-{len(existentes) + 1}"
    log_atual = novo_nome
    ARQUIVO_EXCEL = os.path.join(PASTA_LOGS, f"{log_atual}.xlsx")
    wb = Workbook()
    ws = wb.active
    ws.append(['Data', 'Hora', 'Passagem', 'Tempo (s)'])
    wb.save(ARQUIVO_EXCEL)
    listar_logs_existentes()
    log_index = lista_logs.index(log_atual)
    atualizar_titulo_log()
    leituras = []
    atualizar_lista()

def carregar_log_existente(index):
    global ARQUIVO_EXCEL, log_index, log_atual, leituras
    if 0 <= index < len(lista_logs):
        log_index = index
        log_atual = lista_logs[log_index]
        ARQUIVO_EXCEL = os.path.join(PASTA_LOGS, f"{log_atual}.xlsx")
        wb = load_workbook(ARQUIVO_EXCEL)
        ws = wb.active
        leituras = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            leituras.append({'data': row[0], 'hora': row[1], 'tempo': row[3]})
        atualizar_titulo_log()
        atualizar_lista()

def atualizar_titulo_log():
    lbl_log_titulo.config(text=log_atual)

def salvar_leitura_excel(leitura):
    if not os.path.exists(PASTA_LOGS):
        os.makedirs(PASTA_LOGS)
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

frame_top = tk.Frame(frame_lista, bg='white')
frame_top.pack()

btn_ant = tk.Button(frame_top, text="<", command=lambda: carregar_log_existente(log_index - 1), font=("Arial", 10))
btn_ant.pack(side=tk.LEFT)

lbl_log_titulo = tk.Label(frame_top, text="", font=("Arial", 12, 'bold'))
lbl_log_titulo.pack(side=tk.LEFT, padx=5)

btn_prox = tk.Button(frame_top, text=">", command=lambda: carregar_log_existente(log_index + 1), font=("Arial", 10))
btn_prox.pack(side=tk.LEFT)

lista = tk.Listbox(frame_lista, font=("Arial", 14), selectmode=tk.SINGLE)
lista.pack(fill=tk.BOTH, expand=True)

frame_controles = tk.Frame(root, bg='white')
frame_controles.place(x=240, y=0, width=240, height=320)

btn_iniciar = tk.Button(frame_controles, text="INICIAR", bg='lightcoral', font=("Arial", 14), width=10)
btn_iniciar.pack(pady=5)

btn_novo_log = tk.Button(frame_controles, text="NOVO LOG", bg='blue', fg='white', font=("Arial", 10), command=criar_novo_log)
btn_novo_log.pack(pady=5)

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

# === FUNÇÕES EXISTENTES ===
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
                time.sleep(0.01)
            time.sleep(0.3)
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

# === INICIALIZAÇÃO ===
try:
    listar_logs_existentes()
    if lista_logs:
        carregar_log_existente(len(lista_logs) - 1)
    else:
        criar_novo_log()
    root.mainloop()
finally:
    GPIO.cleanup()
