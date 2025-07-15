import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from openpyxl import Workbook, load_workbook
import threading
import os
import time
import platform

# === CONFIGURAÇÕES ===
if platform.system() == 'Windows':
    TESTE_TOQUE = True  # Ativa simulação por toque no Windows
    USANDO_GPIO = False
    USANDO_TFT = False
else:
    TESTE_TOQUE = False  # Ativa simulação por toque no Windows
    USANDO_GPIO = True
    USANDO_TFT = True
        
if USANDO_GPIO == True:
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        # Configuração especial para evitar conflitos com TFT
        if USANDO_TFT:
            GPIO.setup(SENSOR_LARGADA, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Invertida a lógica
            GPIO.setup(SENSOR_CHEGADA, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Invertida a lógica
        else:
            GPIO.setup(SENSOR_LARGADA, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            GPIO.setup(SENSOR_CHEGADA, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    except Exception as e:
        messagebox.showerror("Erro de GPIO", f"Erro na configuração: {str(e)}")
        USANDO_GPIO = False

# === VARIÁVEIS GLOBAIS ===
sensor_simulado_largada = False
sensor_simulado_chegada = False
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

# ===================================================================
#  INÍCIO DO BLOCO DE TODAS AS FUNÇÕES
#  (Movido para antes da criação da GUI para evitar NameError)
# ===================================================================

def listar_logs_existentes():
    global lista_logs, btn_ant, btn_prox
    if not os.path.exists(PASTA_LOGS):
        os.makedirs(PASTA_LOGS)
    lista_logs = sorted([f[:-5] for f in os.listdir(PASTA_LOGS) if f.endswith('.xlsx')])
    # A atualização dos botões é chamada dentro de carregar_log_existente ou criar_novo_log
    # para garantir que os botões já existam.

def criar_novo_log():
    global ARQUIVO_EXCEL, leituras, log_atual, log_index
    hoje = datetime.now().strftime('%d%m%y')
    listar_logs_existentes() # Atualiza a lista de logs primeiro
    existentes = [f for f in lista_logs if f.startswith(hoje)]
    novo_nome = hoje if not existentes else f"{hoje}-{len(existentes) + 1}"
    
    log_atual = novo_nome
    ARQUIVO_EXCEL = os.path.join(PASTA_LOGS, f"{log_atual}.xlsx")
    wb = Workbook()
    ws = wb.active
    ws.append(['Data', 'Hora', 'Passagem', 'Tempo (s)'])
    wb.save(ARQUIVO_EXCEL)
    
    listar_logs_existentes() # Re-lista para incluir o novo arquivo
    log_index = lista_logs.index(log_atual)
    
    leituras = []
    atualizar_lista()
    atualizar_titulo_log()
    atualizar_botoes_navegacao()

def carregar_log_existente(index):
    global ARQUIVO_EXCEL, log_index, log_atual, leituras
    if 0 <= index < len(lista_logs):
        log_index = index
        log_atual = lista_logs[log_index]
        ARQUIVO_EXCEL = os.path.join(PASTA_LOGS, f"{log_atual}.xlsx")
        try:
            wb = load_workbook(ARQUIVO_EXCEL)
            ws = wb.active
            leituras = []
            for row in ws.iter_rows(min_row=2, values_only=True):
                if row and row[0] is not None:
                    leituras.append({'data': row[0], 'hora': row[1], 'tempo': row[3], 'passagem': row[2]})
            
            atualizar_titulo_log()
            atualizar_lista()
        except Exception as e:
            messagebox.showerror("Erro ao carregar Log", f"Não foi possível carregar o arquivo {log_atual}.xlsx: {e}")
            leituras = []
    
    atualizar_botoes_navegacao()

def atualizar_botoes_navegacao():
    btn_ant.config(state=tk.NORMAL if log_index > 0 else tk.DISABLED)
    btn_prox.config(state=tk.NORMAL if log_index < len(lista_logs) - 1 else tk.DISABLED)

def atualizar_titulo_log():
    lbl_log_titulo.config(text=log_atual)

def salvar_leitura_excel(leitura):
    # ... (código da função sem alterações)
    if not os.path.exists(PASTA_LOGS):
        os.makedirs(PASTA_LOGS)
    if not os.path.exists(ARQUIVO_EXCEL):
        wb = Workbook()
        ws = wb.active
        ws.append(['Data', 'Hora', 'Passagem', 'Tempo (s)'])
    else:
        wb = load_workbook(ARQUIVO_EXCEL)
        ws = wb.active
    
    data = leitura['data']
    hora = leitura['hora']
    tempo = leitura['tempo']
    passagem = leitura['passagem']
    ws.append([data, hora, passagem, tempo])
    wb.save(ARQUIVO_EXCEL)

def leitura_id():
    existente = [l['passagem'] for l in leituras]
    return max(existente + [0]) + 1

def simular_sensor(sensor_id):
    global sensor_simulado_largada, sensor_simulado_chegada
    if not TESTE_TOQUE:
        return
    if sensor_id == SENSOR_LARGADA:
        sensor_simulado_largada = True
        atualizar_circulo(SENSOR_LARGADA, True)
    elif sensor_id == SENSOR_CHEGADA:
        sensor_simulado_chegada = True
        atualizar_circulo(SENSOR_CHEGADA, True)

def atualizar_circulo(sensor_id, ativo):
    cor = 'lime' if ativo else 'darkgreen'
    if sensor_id == SENSOR_LARGADA:
        canvas_largada.itemconfig(circ_largada, fill=cor)
    elif sensor_id == SENSOR_CHEGADA:
        canvas_chegada.itemconfig(circ_chegada, fill=cor)

def monitorar():
    global medindo
    
    # Desabilita o botão durante a operação
    btn_iniciar.config(state=tk.DISABLED)
    
    try:
        if not USANDO_GPIO and not TESTE_TOQUE:
            # =============================================
            # MODO WINDOWS SEM SIMULAÇÃO (APENAS INTERFACE)
            # =============================================
            while medindo:
                time.sleep(0.1)  # Mantém a thread ativa
                
        else:
            # =============================================
            # MODO RASPBERRY PI OU MODO DE TESTE
            # =============================================
            ultimo_estado_largada = False
            ultimo_estado_chegada = False
            
            while medindo:
                # Verifica se estamos usando GPIO ou simulação por toque
                if USANDO_GPIO:
                    # Leitura dos sensores físicos
                    estado_largada = not GPIO.input(SENSOR_LARGADA) if USANDO_TFT else GPIO.input(SENSOR_LARGADA)
                    estado_chegada = not GPIO.input(SENSOR_CHEGADA) if USANDO_TFT else GPIO.input(SENSOR_CHEGADA)
                else:
                    # Modo de teste por toque
                    estado_largada = sensor_simulado_largada
                    estado_chegada = sensor_simulado_chegada
                    # Reseta os sensores simulados após a leitura
                    sensor_simulado_largada = False
                    sensor_simulado_chegada = False
                
                # Detecção de ativação do sensor de largada
                if estado_largada and not ultimo_estado_largada:
                    atualizar_circulo(SENSOR_LARGADA, True)
                    t1 = time.time()
                    
                    # Se for GPIO, espera o sensor ser liberado
                    if USANDO_GPIO:
                        while (not GPIO.input(SENSOR_LARGADA) if USANDO_TFT else GPIO.input(SENSOR_LARGADA)):
                            if not medindo: break
                            time.sleep(0.01)
                    
                    time.sleep(0.1)  # Debounce
                    
                    # Procura pela chegada
                    chegada_detectada = False
                    while medindo and not chegada_detectada:
                        if USANDO_GPIO:
                            chegada_detectada = not GPIO.input(SENSOR_CHEGADA) if USANDO_TFT else GPIO.input(SENSOR_CHEGADA)
                        else:
                            chegada_detectada = sensor_simulado_chegada
                            sensor_simulado_chegada = False
                        
                        if chegada_detectada:
                            atualizar_circulo(SENSOR_CHEGADA, True)
                            t2 = time.time()
                            tempo = round(t2 - t1, 2)
                            
                            # Registra a leitura
                            dt = datetime.now()
                            leitura = {
                                'data': dt.strftime('%d/%m/%Y'),
                                'hora': dt.strftime('%H:%M:%S'),
                                'tempo': tempo,
                                'passagem': leitura_id()
                            }
                            leituras.append(leitura)
                            salvar_leitura_excel(leitura)
                            atualizar_lista()
                            
                            # Feedback visual
                            for _ in range(5):
                                if not medindo: break
                                time.sleep(0.1)
                            
                            break
                        
                        time.sleep(0.01)
                    
                    # Desativa os círculos
                    atualizar_circulo(SENSOR_LARGADA, False)
                    atualizar_circulo(SENSOR_CHEGADA, False)
                
                # Atualiza os estados anteriores
                ultimo_estado_largada = estado_largada
                ultimo_estado_chegada = estado_chegada
                
                time.sleep(0.01)
    
    except Exception as e:
        print(f"Erro durante monitoramento: {e}")
    finally:
        # Restaura o estado do botão
        btn_iniciar.config(state=tk.NORMAL)
        atualizar_circulo(SENSOR_LARGADA, False)
        atualizar_circulo(SENSOR_CHEGADA, False)

def atualizar_lista():
    lista.delete(0, tk.END)
    for l in sorted(leituras, key=lambda x: x['passagem']):
        lista.insert(tk.END, f"{l['passagem']:02} - {l['tempo']}s")

def iniciar_parar():
    global medindo, thread_leitura
    if not medindo:
        if not ARQUIVO_EXCEL:
            messagebox.showwarning("Sem Log", "Crie um novo log antes de iniciar a cronometragem.")
            return
        
        # Atualiza os círculos apenas se estiver usando GPIO
        if USANDO_GPIO and USANDO_TFT:
            atualizar_circulo(SENSOR_LARGADA, not GPIO.input(SENSOR_LARGADA))
            atualizar_circulo(SENSOR_CHEGADA, not GPIO.input(SENSOR_CHEGADA))
        
        medindo = True
        thread_leitura = threading.Thread(target=monitorar)
        thread_leitura.daemon = True
        thread_leitura.start()
        btn_iniciar.config(text="PARAR", bg='red', fg='white')  # Muda cor e texto
    else:
        medindo = False
        # Aguarda a thread terminar (com timeout para não travar)
        if thread_leitura is not None:
            thread_leitura.join(timeout=0.5)
        btn_iniciar.config(text="INICIAR", bg='lightgreen', fg='black')  # Volta ao estado inicial
        atualizar_circulo(SENSOR_LARGADA, False)
        atualizar_circulo(SENSOR_CHEGADA, False)

def excluir_leitura():
    sel = lista.curselection()
    if not sel:
        messagebox.showinfo("Nenhuma Seleção", "Por favor, selecione uma leitura para excluir.")
        return
    
    passagem_a_remover_str = lista.get(sel[0]).split(' ')[0]
    passagem_a_remover = int(passagem_a_remover_str)
    
    leitura_idx_real = next((i for i, l in enumerate(leituras) if l['passagem'] == passagem_a_remover), -1)
            
    if leitura_idx_real == -1:
        messagebox.showerror("Erro", "Não foi possível encontrar a leitura para excluir.")
        return

    if messagebox.askyesno("Confirmar Exclusão", f"Tem certeza que deseja excluir a passagem {passagem_a_remover:02}?"):
        try:
            wb = load_workbook(ARQUIVO_EXCEL)
            ws = wb.active
            row_to_delete = -1
            for i in range(ws.max_row, 1, -1):
                if ws.cell(row=i, column=3).value == passagem_a_remover:
                    row_to_delete = i
                    break
            
            if row_to_delete != -1:
                ws.delete_rows(row_to_delete)
                wb.save(ARQUIVO_EXCEL)
                leituras.pop(leitura_idx_real)
                atualizar_lista()
            else:
                messagebox.showwarning("Erro de Exclusão", "Leitura não encontrada na planilha Excel.")

        except Exception as e:
            messagebox.showerror("Erro ao Excluir", f"Erro ao excluir leitura do Excel: {e}")

def inicializar_app():
    listar_logs_existentes()
    if lista_logs:
        carregar_log_existente(len(lista_logs) - 1)
    else:
        criar_novo_log()
# ===================================================================
#  FIM DO BLOCO DE FUNÇÕES
# ===================================================================


# === CONFIGURAÇÃO GPIO ===
if USANDO_GPIO:
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(SENSOR_LARGADA, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(SENSOR_CHEGADA, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    except Exception as e:
        messagebox.showerror("Erro de GPIO", f"Não foi possível configurar os pinos GPIO: {e}")
        USANDO_GPIO = False

# === GUI (Interface Gráfica) ===
root = tk.Tk()
root.title("Cronometragem")
root.attributes('-fullscreen', True)
root.configure(bg='white')

frame_lista = tk.Frame(root, bg='white')
frame_lista.place(x=0, y=0, width=240, height=320)

frame_top = tk.Frame(frame_lista, bg='white')
frame_top.pack()

btn_ant = tk.Button(frame_top, text="<", command=lambda: carregar_log_existente(log_index - 1), font=("Arial", 10))
btn_ant.pack(side=tk.LEFT)

lbl_log_titulo = tk.Label(frame_top, text="", font=("Arial", 12, 'bold'), bg='white')
lbl_log_titulo.pack(side=tk.LEFT, padx=5)

btn_prox = tk.Button(frame_top, text=">", command=lambda: carregar_log_existente(log_index + 1), font=("Arial", 10))
btn_prox.pack(side=tk.LEFT)

lista = tk.Listbox(frame_lista, font=("Arial", 14), selectmode=tk.SINGLE)
lista.pack(fill=tk.BOTH, expand=True)

frame_controles = tk.Frame(root, bg='white')
frame_controles.place(x=240, y=0, width=240, height=320)

btn_iniciar = tk.Button(
    frame_controles, 
    text="INICIAR", 
    bg='lightgreen', 
    fg='black', 
    font=("Arial", 14), 
    width=10, 
    command=iniciar_parar,
    activebackground='red',  # Cor quando pressionado
    activeforeground='white'  # Texto quando pressionado
)
btn_iniciar.pack(pady=5)

btn_novo_log = tk.Button(frame_controles, text="NOVO LOG", bg='blue', fg='white', font=("Arial", 10), command=criar_novo_log)
btn_novo_log.pack(pady=5)

btn_excluir = tk.Button(frame_controles, text="EXCLUIR", bg='red', fg='white', font=("Arial", 10), command=excluir_leitura)
btn_excluir.pack(pady=5)

lbl_largada = tk.Label(frame_controles, text="LARGADA", font=("Arial", 10), bg='white')
lbl_largada.pack()
canvas_largada = tk.Canvas(frame_controles, width=50, height=50, bg='white', highlightthickness=0)
circ_largada = canvas_largada.create_oval(5, 5, 45, 45, fill='darkgreen')
if TESTE_TOQUE:
    canvas_largada.bind("<Button-1>", lambda e: simular_sensor(SENSOR_LARGADA))
canvas_largada.pack()

lbl_chegada = tk.Label(frame_controles, text="CHEGADA", font=("Arial", 10), bg='white')
lbl_chegada.pack()
canvas_chegada = tk.Canvas(frame_controles, width=50, height=50, bg='white', highlightthickness=0)
circ_chegada = canvas_chegada.create_oval(5, 5, 45, 45, fill='darkgreen')
if TESTE_TOQUE:
    canvas_chegada.bind("<Button-1>", lambda e: simular_sensor(SENSOR_CHEGADA))
canvas_chegada.pack()


# === INICIALIZAÇÃO E LOOP PRINCIPAL ===
inicializar_app()
root.mainloop()

# === LIMPEZA AO FECHAR ===
if USANDO_GPIO:
    GPIO.cleanup()