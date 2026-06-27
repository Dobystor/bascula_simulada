import socket
import threading
import json
import time
import random
import re
import os
import uuid
from datetime import datetime
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def get_mac_address():
    try:
        mac = uuid.getnode()
        return ':'.join(['{:02x}'.format((mac >> elements) & 0xff) for elements in range(40, -1, -8)]).upper()
    except:
        return "00:00:00:00:00:00"

HOST_IP = get_local_ip()
BASCULA_PORT, SEMAFORO_PORT, WEB_PORT = 4001, 44001, 8080

config = {"modo": "auto", "valor_manual": 70, "rango": [60, 95], "intervalo_bascula": 1.0}
peso_actual = 0
historial_semaforo = []
logs_bascula, logs_semaforo = [], []
msg_id_counter = 0

app = FastAPI()

def añadir_log(lista, mensaje):
    t = datetime.now().strftime("%H:%M:%S")
    lista.append(f"[{t}] {mensaje}")
    if len(lista) > 100: lista.pop(0)

@app.get("/", response_class=HTMLResponse)
def index():
    content = """
    <html>
    <head>
        <meta charset="utf-8">
        <title>SIMULATOR WM</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=VT323&display=swap" rel="stylesheet">
        <style>
                        :root {
                --brand-blue: #0a5da7;
                --brand-cyan: #36b0c9;
                --brand-navy: #002b49;
                --brand-gray: #c1c5c8;
            
                --bg-main: #010b14;
                --bg-panel: rgba(0, 43, 73, 0.3);
                --bg-info: rgba(0, 43, 73, 0.4);
                --bg-monitor: rgba(2, 6, 12, 0.85);
                --border-acrylic-1: rgba(193, 197, 200, 0.15);
                --border-acrylic-2: rgba(193, 197, 200, 0.05);
                --border-focus: rgba(54, 176, 201, 0.6);
                
                --nixie-core: #ffffff;
                --nixie-glow-1: var(--brand-cyan);
                --nixie-glow-2: var(--brand-blue);
                --nixie-glow-3: var(--brand-navy);
                
                --text-main: var(--brand-gray);
                --text-log: var(--brand-cyan);
                
                --glass-shadow: 0 10px 30px rgba(0, 0, 0, 0.9);
                --neon-shadow: 0 0 5px var(--nixie-core), 0 0 10px var(--nixie-glow-1), 0 0 20px var(--nixie-glow-2), 0 0 40px var(--nixie-glow-3);
            }

            * { box-sizing: border-box; }
            
            body { 
                background: var(--bg-main) url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"><rect width="4" height="4" fill="%23010b14"/><rect width="1" height="1" fill="%23001a2e"/></svg>'); 
                color: var(--text-main); font-family: 'Share Tech Mono', monospace; 
                margin: 0; padding: 2vh 2vw; display: flex; justify-content: center; align-items: center;
                height: 100vh; overflow: hidden;
            }
            
            .main-container { 
                display: grid; grid-template-columns: 350px 1fr; gap: 20px; 
                width: 100%; max-width: 1400px; height: 94vh; 
            }
            .column { display: flex; flex-direction: column; gap: 20px; height: 100%; overflow: hidden; }
            
            /* Emulating the stacked acrylic clear base */
            .panel { 
                background: var(--bg-panel); backdrop-filter: blur(5px); -webkit-backdrop-filter: blur(5px);
                padding: 20px; border-radius: 8px; 
                border-top: 2px solid var(--border-acrylic-1);
                border-left: 2px solid var(--border-acrylic-1);
                border-right: 2px solid var(--border-acrylic-2);
                border-bottom: 2px solid var(--border-acrylic-2);
                box-shadow: inset 0 0 20px rgba(0,0,0,0.8), var(--glass-shadow);
                display: flex; flex-direction: column; position: relative; overflow: hidden; 
                transition: border 0.3s ease; 
            }
            .panel::after {
                content: ''; position: absolute; top:0; left:0; right:0; bottom:0;
                box-shadow: inset 0 0 2px rgba(255,255,255,0.1); pointer-events: none; border-radius: 8px;
            }
            
            h2 { 
                margin: 0 0 15px 0; font-size: 1.1em; font-weight: 800; letter-spacing: 2px;
                text-transform: uppercase; color: var(--nixie-glow-1); display: flex; align-items: center; gap: 8px;
                text-shadow: 0 0 10px rgba(54, 176, 201, 0.5);
            }
            h2 .dot { width:8px; height:8px; background:var(--nixie-core); border-radius:50%; box-shadow: var(--neon-shadow); }
            
            .info-bar { 
                display: grid; grid-template-columns: 1fr 1fr; gap: 8px; background: var(--bg-info); 
                padding: 15px; border-radius: 6px; margin-bottom: 20px; font-family: 'Share Tech Mono', monospace; 
                font-size: 0.85em; color: var(--nixie-glow-1); 
                border: 1px solid rgba(54,176,201,0.2); box-shadow: inset 0 0 10px rgba(0,0,0,0.8);
            }
            .info-bar span { display: flex; flex-direction: column; }
            .info-bar span small { color: var(--text-main); font-size: 0.65em; opacity: 0.8; margin-bottom: 2px; letter-spacing: 1px;}
            
            /* TUBE DISPLAY EFFECT */
            .display-peso { 
                font-family: 'VT323', monospace; font-size: 8em; text-align: center; 
                background: linear-gradient(180deg, rgba(10,10,10,0.9) 0%, rgba(0,0,0,1) 50%, rgba(10,10,10,0.9) 100%);
                margin: 0 0 20px 0; border-radius: 40px; padding: 20px; 
                color: var(--nixie-core); 
                border: 2px solid rgba(255,255,255,0.05); 
                box-shadow: inset 0 -5px 15px rgba(54, 176, 201, 0.05), inset 0 5px 15px rgba(0,0,0,1), 0 10px 20px rgba(0,0,0,0.8);
                text-shadow: var(--neon-shadow); flex-shrink: 0; line-height: 1; letter-spacing: 15px;
                position: relative; overflow: hidden;
            }
            .display-peso::before {
                content: ''; position: absolute; top: 5%; left: 5%; right: 5%; height: 30%;
                background: linear-gradient(180deg, rgba(255,255,255,0.08) 0%, transparent 100%);
                border-radius: 30px 30px 0 0; pointer-events: none;
            }
            .display-peso::after {
                content: ''; position: absolute; top:0; left:0; right:0; bottom:0;
                background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.3) 3px, rgba(0,0,0,0.3) 4px),
                            repeating-linear-gradient(90deg, transparent, transparent 2px, rgba(0,0,0,0.2) 3px, rgba(0,0,0,0.2) 4px);
                pointer-events: none; opacity: 0.8; mix-blend-mode: overlay;
            }
            
            .led-container { 
                background: var(--bg-monitor); 
                border: 2px solid rgba(255,255,255,0.05); 
                flex-grow: 1; min-height: 140px;
                overflow: hidden; position: relative; display: flex; align-items: center; border-radius: 30px; 
                box-shadow: inset 0 0 30px rgba(0,0,0,1);
            }
            .led-container::before {
                content: ''; position: absolute; top: 5%; left: 2%; right: 2%; height: 30%;
                background: linear-gradient(180deg, rgba(255,255,255,0.05) 0%, transparent 100%);
                border-radius: 20px 20px 0 0; pointer-events: none; z-index: 2;
            }
            .led-container::after {
                content: ''; position: absolute; top:0; left:0; right:0; bottom:0;
                background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.3) 3px, rgba(0,0,0,0.3) 4px),
                            repeating-linear-gradient(90deg, transparent, transparent 2px, rgba(0,0,0,0.2) 3px, rgba(0,0,0,0.2) 4px);
                pointer-events: none; opacity: 0.8; mix-blend-mode: overlay; z-index: 0;
            }
            
            .led-text { 
                white-space: nowrap; position: absolute; font-family: 'VT323', monospace; font-size: 6rem; 
                font-weight: normal; left: 100%; will-change: transform; 
                color: var(--nixie-core);
                text-shadow: var(--neon-shadow);
                letter-spacing: 5px; z-index: 1;
            }
            @keyframes marquee { 0% { left: 100%; transform: translateX(0); } 100% { left: 0%; transform: translateX(-100%); } }
            
            .fullscreen-mode { 
                position: fixed !important; top: 0 !important; left: 0 !important; width: 100vw !important; height: 100vh !important; 
                z-index: 9999; background: var(--bg-main) !important; display: flex !important; flex-direction: column; 
                align-items: center; justify-content: center; border: none !important; border-radius: 0 !important;
                padding: 5vh 5vw !important; box-shadow: inset 0 0 100px rgba(54,176,201,0.05);
            }
            .fullscreen-mode .display-peso { font-size: 25vh; width: 100%; margin-bottom: 5vh; max-width: 1400px; }
            .fullscreen-mode .led-container { width: 100%; height: 35vh; max-width: 1400px; }
            .fullscreen-mode .led-text { font-size: 30vh; }
            
            .exit-fs { 
                display: none; position: fixed; top: 30px; right: 30px; z-index: 10000; 
                background: rgba(10,93,167,0.1); color: #0a5da7; border: 1px solid rgba(10,93,167,0.5); 
                padding: 12px 24px; border-radius: 6px; font-weight: bold; font-family: 'Share Tech Mono'; letter-spacing: 2px;
                cursor: pointer; backdrop-filter: blur(5px); transition: all 0.3s ease; text-shadow: 0 0 5px rgba(10,93,167,0.5);
            }
            .exit-fs:hover { background: rgba(10,93,167,0.3); box-shadow: 0 0 20px rgba(10,93,167,0.6); }
            
            .terminal { display: flex; flex-direction: column; height: 100%; }
            .terminal-header { 
                background: rgba(0,43,73,0.8); padding: 8px 15px; border-radius: 4px 4px 0 0;
                display: flex; gap: 8px; align-items: center; border-bottom: 1px solid rgba(54,176,201,0.2);
            }
            .terminal-title { font-size: 0.8em; color: var(--nixie-glow-2); font-family: 'Share Tech Mono'; font-weight:bold; letter-spacing: 1px; text-transform: uppercase; }
            
            .log-box { 
                background: var(--bg-monitor); padding: 15px; border-radius: 0 0 4px 4px; font-family: 'Share Tech Mono', monospace; 
                font-size: 0.9rem; line-height: 1.5; flex-grow: 1; overflow-y: auto; color: var(--text-log); 
                box-shadow: inset 0 5px 20px rgba(0,0,0,0.8); text-shadow: 0 0 3px rgba(54,176,201,0.5);
            }
            .log-box::-webkit-scrollbar { width: 6px; }
            .log-box::-webkit-scrollbar-track { background: transparent; }
            .log-box::-webkit-scrollbar-thumb { background: rgba(54,176,201,0.3); border-radius: 3px; }
            .log-box::-webkit-scrollbar-thumb:hover { background: rgba(54,176,201,0.6); }
            
            button.action-btn { 
                background: rgba(54, 176, 201, 0.1); color: var(--nixie-glow-1); font-family: 'Share Tech Mono', monospace; font-weight: 700; 
                font-size: 1.2em; letter-spacing: 2px; cursor: pointer; border: 1px solid rgba(54,176,201,0.4); 
                padding: 16px; border-radius: 6px; margin-top: auto; transition: all 0.2s; 
                box-shadow: inset 0 0 10px rgba(54,176,201,0.1), 0 4px 10px rgba(0,0,0,0.5);
                text-transform: uppercase; text-shadow: 0 0 5px rgba(54,176,201,0.5);
            }
            button.action-btn:hover { background: rgba(54,176,201,0.2); border-color: rgba(54,176,201,0.8); box-shadow: inset 0 0 15px rgba(54,176,201,0.3), 0 0 15px rgba(54,176,201,0.4); text-shadow: 0 0 10px rgba(54,176,201,0.8); }
            button.action-btn:active { transform: translateY(2px); }
            
            .input-group { margin-bottom: 15px; position: relative; }
            input, select { 
                background: rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.1); color: var(--nixie-glow-1); 
                font-family: 'Share Tech Mono'; font-weight: bold; font-size: 1.1rem; padding: 10px 15px; border-radius: 4px; 
                width: 100%; outline: none; transition: all 0.3s ease; box-shadow: inset 0 2px 10px rgba(0,0,0,0.8); appearance: none;
                text-shadow: 0 0 5px rgba(54,176,201,0.3);
            }
            input:focus, select:focus { border-color: var(--nixie-glow-2); box-shadow: inset 0 2px 10px rgba(0,0,0,0.8), 0 0 10px rgba(54,176,201,0.2); }
            label { font-size: 0.75em; color: var(--text-main); font-weight: bold; text-transform: uppercase; margin-bottom: 8px; display: block; letter-spacing: 1px; }
            
            .hidden { display: none !important; }
            .animate-in { animation: fadeIn 0.4s ease forwards; }
            @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
            
            .confetti { position: fixed; width: 4px; height: 12px; pointer-events: none; z-index: 10000; border-radius: 10px; box-shadow: var(--neon-shadow); background: var(--nixie-core); opacity: 0.8; }
            
            .select-wrapper { position: relative; }
            .select-wrapper::after { content: '▼'; font-size: 0.7em; color: var(--nixie-glow-2); position: absolute; right: 15px; top: 50%; transform: translateY(-50%); pointer-events: none; text-shadow: 0 0 5px rgba(54,176,201,0.5); }
            .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
            .expand-btn-container { display: flex; justify-content: flex-end; margin-top: 15px; }
            button.expand-btn {
                background: transparent; color: var(--text-main); border: 1px solid rgba(255,255,255,0.1);
                padding: 8px 15px; border-radius: 4px; font-family: 'Share Tech Mono'; font-weight: bold; font-size: 0.85em;
                cursor: pointer; transition: all 0.3s ease; display: flex; align-items: center; gap: 8px; opacity: 0.7;
            }
            button.expand-btn:hover { opacity: 1; border-color: var(--nixie-glow-2); color: var(--nixie-glow-1); box-shadow: inset 0 0 10px rgba(54,176,201,0.2); text-shadow: 0 0 5px rgba(54,176,201,0.5); }

            :root.light-mode {
                --bg-main: #f0f4f8;
                --bg-panel: rgba(255, 255, 255, 0.7);
                --bg-info: rgba(255, 255, 255, 0.9);
                --text-main: var(--brand-navy);
                --glass-shadow: 0 10px 30px rgba(10, 93, 167, 0.1);
            }
            :root.light-mode body {
                background: var(--bg-main) url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"><rect width="4" height="4" fill="%23E2E8F0"/><rect width="1" height="1" fill="%23CBD5E1"/></svg>'); 
            }
            :root.light-mode .panel:not(#panel_monitor):not(.keep-dark) {
                background: var(--bg-panel);
                box-shadow: inset 0 0 10px rgba(255,255,255,0.8), var(--glass-shadow);
                border-top: 2px solid rgba(255, 255, 255, 0.9);
                border-left: 2px solid rgba(255, 255, 255, 0.9);
                border-right: 2px solid rgba(200, 200, 200, 0.5);
                border-bottom: 2px solid rgba(200, 200, 200, 0.5);
                color: var(--text-main);
            }
            :root.light-mode input, :root.light-mode select {
                background: rgba(255, 255, 255, 0.8);
                color: var(--nixie-glow-2);
                border: 1px solid rgba(0, 0, 0, 0.2);
                box-shadow: inset 0 2px 5px rgba(0,0,0,0.05);
                text-shadow: none;
            }
            :root.light-mode label { color: var(--text-main); }
            :root.light-mode h2 { text-shadow: none; filter: drop-shadow(0 0 3px rgba(54,176,201,0.4)); }
            :root.light-mode #panel_monitor h2 { text-shadow: 0 0 10px rgba(54, 176, 201, 0.5); filter: none; }
            :root.light-mode .info-bar { border: 1px solid rgba(54,176,201,0.3); background: rgba(255, 255, 255, 0.8); box-shadow: none; }
            :root.light-mode .info-bar span { color: var(--nixie-glow-2); }
            :root.light-mode .info-bar span small { color: var(--text-main); }
            :root.light-mode button.expand-btn { color: var(--text-main); border-color: rgba(0,0,0,0.2); }
            :root.light-mode button.expand-btn:hover { color: var(--nixie-glow-2); border-color: var(--nixie-glow-2); box-shadow: none; }
            
            .theme-toggle {
                position: fixed; bottom: 30px; right: 30px; z-index: 9999;
                background: rgba(54,176,201,0.1); color: var(--nixie-glow-1);
                border: 1px solid rgba(54,176,201,0.5);
                padding: 12px 20px; border-radius: 6px; font-weight: bold;
                font-family: 'Share Tech Mono'; letter-spacing: 2px;
                cursor: pointer; backdrop-filter: blur(5px); transition: all 0.3s ease;
                text-shadow: 0 0 5px rgba(54,176,201,0.5);
                box-shadow: 0 4px 10px rgba(0,0,0,0.5);
            }
            .theme-toggle:hover { background: rgba(54,176,201,0.3); box-shadow: 0 0 20px rgba(54,176,201,0.6); transform: scale(1.05); }
            .theme-toggle:active { transform: scale(0.95); }

            :root.light-mode {
                --bg-main: #f0f4f8;
                --bg-panel: rgba(255, 255, 255, 0.7);
                --bg-info: rgba(255, 255, 255, 0.9);
                --text-main: var(--brand-navy);
                --glass-shadow: 0 10px 30px rgba(10, 93, 167, 0.1);
            }
            :root.light-mode body {
                background: var(--bg-main) url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"><rect width="4" height="4" fill="%23E2E8F0"/><rect width="1" height="1" fill="%23CBD5E1"/></svg>'); 
            }
            :root.light-mode .panel:not(#panel_monitor):not(.keep-dark) {
                background: var(--bg-panel);
                box-shadow: inset 0 0 10px rgba(255,255,255,0.8), var(--glass-shadow);
                border-top: 2px solid rgba(255, 255, 255, 0.9);
                border-left: 2px solid rgba(255, 255, 255, 0.9);
                border-right: 2px solid rgba(200, 200, 200, 0.5);
                border-bottom: 2px solid rgba(200, 200, 200, 0.5);
                color: var(--text-main);
            }
            :root.light-mode input, :root.light-mode select {
                background: rgba(255, 255, 255, 0.8);
                color: var(--nixie-glow-2);
                border: 1px solid rgba(0, 0, 0, 0.2);
                box-shadow: inset 0 2px 5px rgba(0,0,0,0.05);
                text-shadow: none;
            }
            :root.light-mode label { color: var(--text-main); }
            :root.light-mode h2 { text-shadow: none; filter: drop-shadow(0 0 3px rgba(54,176,201,0.4)); }
            :root.light-mode #panel_monitor h2 { text-shadow: 0 0 10px rgba(54, 176, 201, 0.5); filter: none; }
            :root.light-mode .info-bar { border: 1px solid rgba(54,176,201,0.3); background: rgba(255, 255, 255, 0.8); box-shadow: none; }
            :root.light-mode .info-bar span { color: var(--nixie-glow-2); }
            :root.light-mode .info-bar span small { color: var(--text-main); }
            :root.light-mode button.expand-btn { color: var(--text-main); border-color: rgba(0,0,0,0.2); }
            :root.light-mode button.expand-btn:hover { color: var(--nixie-glow-2); border-color: var(--nixie-glow-2); box-shadow: none; }
            
            .theme-toggle {
                position: fixed; bottom: 30px; right: 30px; z-index: 9999;
                background: rgba(54,176,201,0.1); color: var(--nixie-glow-1);
                border: 1px solid rgba(54,176,201,0.5);
                padding: 12px 20px; border-radius: 6px; font-weight: bold;
                font-family: 'Share Tech Mono'; letter-spacing: 2px;
                cursor: pointer; backdrop-filter: blur(5px); transition: all 0.3s ease;
                text-shadow: 0 0 5px rgba(54,176,201,0.5);
                box-shadow: 0 4px 10px rgba(0,0,0,0.5);
            }
            .theme-toggle:hover { background: rgba(54,176,201,0.3); box-shadow: 0 0 20px rgba(54,176,201,0.6); transform: scale(1.05); }
            .theme-toggle:active { transform: scale(0.95); }

            /* Yahtzee Minigame (Tech UI) */
            #yahtzee-overlay { display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: var(--bg-main); z-index: 100000; align-items: center; justify-content: center; flex-direction: column; overflow: hidden; font-family: 'Share Tech Mono', monospace;}
            #yz-board { display: flex; width: 950px; height: 600px; background: rgba(0,25,45,0.9); border: 2px solid var(--brand-blue); border-radius: 8px; box-shadow: 0 0 30px rgba(54,176,201,0.2), inset 0 0 20px rgba(0,0,0,0.8); overflow: hidden;}
            #yz-left { width: 350px; background: var(--bg-panel); padding: 20px; display: flex; flex-direction: column; align-items: center; justify-content: space-between; border-right: 2px dashed rgba(54,176,201,0.3); }
            #yz-right { flex: 1; padding: 20px; overflow-y: auto; }
            .yz-dice-container { display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; margin: 20px 0; }
            .yz-die { width: 50px; height: 50px; background: var(--bg-monitor); border: 1px solid var(--brand-cyan); border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 2.5rem; cursor: pointer; user-select: none; transition: transform 0.2s; box-shadow: inset 0 2px 10px rgba(0,0,0,0.8); color: var(--nixie-core); text-shadow: 0 0 10px var(--brand-cyan);}
            .yz-die.held { background: rgba(54,176,201,0.3); transform: translateY(4px); box-shadow: 0 0 0 transparent; border-color: var(--brand-cyan); color: var(--brand-cyan); }
            .yz-btn { background: rgba(54, 176, 201, 0.1); color: var(--nixie-glow-1); border: 1px solid rgba(54,176,201,0.4); padding: 15px 30px; font-family: 'Share Tech Mono', monospace; font-size: 1.5rem; border-radius: 6px; cursor: pointer; box-shadow: inset 0 0 10px rgba(54,176,201,0.1), 0 4px 10px rgba(0,0,0,0.5); transition: all 0.2s; font-weight: bold; letter-spacing: 2px;}
            .yz-btn:hover { background: rgba(54,176,201,0.2); border-color: rgba(54,176,201,0.8); box-shadow: inset 0 0 15px rgba(54,176,201,0.3), 0 0 15px rgba(54,176,201,0.4); text-shadow: 0 0 10px rgba(54,176,201,0.8); transform: translateY(2px); }
            .yz-btn:disabled { background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.2); border-color: rgba(255,255,255,0.1); box-shadow: none; cursor: not-allowed; text-shadow: none;}
            .yz-table { width: 100%; border-collapse: collapse; font-size: 1rem; color: var(--brand-gray); }
            .yz-table th, .yz-table td { border: 1px solid rgba(54,176,201,0.2); padding: 6px; text-align: center; }
            .yz-table th { background: rgba(0,43,73,0.8); color: var(--brand-cyan); font-weight: bold; letter-spacing: 1px; }
            .yz-score-cell { cursor: pointer; background: rgba(0,0,0,0.3); transition: background 0.2s; font-weight: bold; position: relative; }
            .yz-score-cell.active-p0:hover:not(.filled) { background: rgba(54,176,201,0.2); color: var(--nixie-core); }
            .yz-score-cell.active-p0:not(.filled):hover::after { content: attr(data-preview); color: var(--brand-cyan); opacity: 0.8; font-style: italic;}
            .yz-score-cell.filled { cursor: default; background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.4); }
            #yz-status { font-family: 'Share Tech Mono', monospace; font-size: 1.5rem; color: var(--brand-cyan); text-align: center; margin-bottom: 10px; line-height: 1.2; text-shadow: 0 0 5px rgba(54,176,201,0.5); font-weight: bold;}
            #yz-tole-avatar { width: 150px; height: 150px; background: url('/tole.webp') no-repeat center/contain; border-radius: 50%; box-shadow: inset 0 0 20px rgba(54,176,201,0.6), 0 0 15px rgba(54,176,201,0.3); margin-bottom: 20px; border: 2px solid var(--brand-blue); filter: drop-shadow(0 0 8px rgba(54,176,201,0.5));}
            #game-close-btn { position: absolute; top: 20px; right: 20px; background: rgba(54,176,201,0.1); color: var(--brand-cyan); border: 1px solid rgba(54,176,201,0.5); padding: 10px 20px; border-radius: 6px; cursor: pointer; font-family: 'Share Tech Mono', monospace; font-weight: bold; font-size: 1rem; transition: all 0.3s; z-index: 100001; letter-spacing: 1px; }
            #game-close-btn:hover { background: rgba(54,176,201,0.3); box-shadow: 0 0 15px rgba(54,176,201,0.4); color: var(--nixie-core); }
            
            :root.light-mode #yz-board { background: #E2E8F0; }
            :root.light-mode .yz-table { color: var(--brand-navy); }
            :root.light-mode .yz-die { background: #FFF; color: var(--brand-blue); border-color: rgba(0,0,0,0.2); box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-shadow: none; }
            :root.light-mode .yz-die.held { background: rgba(54,176,201,0.2); border-color: var(--brand-cyan); }
            :root.light-mode .yz-btn { background: #FFF; color: var(--brand-blue); border-color: rgba(0,0,0,0.2); box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-shadow: none; }
            :root.light-mode .yz-score-cell { background: rgba(255,255,255,0.8); }
            :root.light-mode .yz-score-cell.active-p0:hover:not(.filled) { background: rgba(54,176,201,0.3); color: var(--brand-navy); }
            :root.light-mode .yz-score-cell.filled { background: rgba(0,0,0,0.05); color: rgba(0,0,0,0.6); }
            :root.light-mode .yz-score-cell.active-p0:not(.filled):hover::after { color: var(--brand-navy); }
            :root.light-mode #yz-tole-avatar { box-shadow: 0 2px 10px rgba(0,0,0,0.1); border-color: rgba(0,0,0,0.1); }
            :root.light-mode #logoImg { filter: invert(0.8) sepia(1) hue-rotate(180deg) saturate(3) brightness(0.7) !important; opacity: 1 !important; }
            @keyframes evilToleShake {
                0% { transform: translate(2px, 1px) rotate(0deg); filter: sepia(1) hue-rotate(-50deg) saturate(8) drop-shadow(0 0 20px red); box-shadow: inset 0 0 30px red, 0 0 20px red; border-color: red;}
                25% { transform: translate(-3px, 0px) rotate(3deg); filter: sepia(1) hue-rotate(-50deg) saturate(10) drop-shadow(0 0 40px red); box-shadow: inset 0 0 50px red, 0 0 40px red;}
                50% { transform: translate(0px, 2px) rotate(-3deg); filter: sepia(1) hue-rotate(-50deg) saturate(6) drop-shadow(0 0 20px red); box-shadow: inset 0 0 30px red, 0 0 20px red;}
                75% { transform: translate(2px, -2px) rotate(3deg); filter: sepia(1) hue-rotate(-50deg) saturate(10) drop-shadow(0 0 40px red); box-shadow: inset 0 0 50px red, 0 0 40px red;}
                100% { transform: translate(2px, 1px) rotate(0deg); filter: sepia(1) hue-rotate(-50deg) saturate(8) drop-shadow(0 0 20px red); box-shadow: inset 0 0 30px red, 0 0 20px red; border-color: red;}
            }
            .evil-tole { animation: evilToleShake 0.15s infinite alternate !important; }
        </style>
    </head>
    <body>
        <img id="toleImg" src="/tole.webp" style="display:none; position:fixed; top:50%; left:50%; transform:translate(-50%, -50%); z-index:99999; max-width:80vw; max-height:80vh; border-radius:20px; box-shadow: 0 0 80px 20px rgba(255,0,0,0.8); pointer-events:none; filter: sepia(100%) hue-rotate(-45deg) saturate(500%) contrast(1.5);">
        
        <button id="exitBtn" class="exit-fs" onclick="closeFS()">✕ SALIR (ESC)</button>
        
        <button class="theme-toggle" onclick="document.documentElement.classList.toggle('light-mode')">🌓 CAMBIAR TEMA</button>
        
        <div class="main-container">
            <!-- Left Panel -->
            <div class="column">
                <div class="panel" style="flex:1">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 15px;">
                        <h2 style="margin:0;"><span class="dot"></span> TABLERO DE CONTROL</h2>
                        <img id="logoImg" src="/logo" style="height: 35px; opacity: 0.85; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.5));" alt="Becker Lasec">
                    </div>
                    
                    <div class="info-bar">
                        <span><small>IP ADDRESS</small>""" + str(get_local_ip()) + """</span>
                        <span><small>MAC ADDR</small>""" + str(get_mac_address()) + """</span>
                        <span><small>PORT BÁSC.</small>""" + str(BASCULA_PORT) + """</span>
                        <span><small>PORT SEMÁF.</small>""" + str(SEMAFORO_PORT) + """</span>
                    </div>

                    <div class="input-group select-wrapper">
                        <label>MODO DE PESAJE</label>
                        <select id="modo" onchange="updateUI()">
                            <option value="auto">AUTOMÁTICO</option>
                            <option value="manual">MANUAL</option>
                        </select>
                    </div>

                    <div id="ui-manual" class="hidden animate-in">
                        <div class="input-group">
                            <label>PESO MANUAL (TONS)</label>
                            <input type="number" id="manual" value="70">
                        </div>
                    </div>

                    <div id="ui-auto" class="animate-in">
                        <div class="grid-2">
                            <div class="input-group">
                                <label>MÍNIMO</label>
                                <input type="number" id="rmin" value="60">
                            </div>
                            <div class="input-group">
                                <label>MÁXIMO</label>
                                <input type="number" id="rmax" value="95">
                            </div>
                        </div>
                    </div>
                    
                    <div class="input-group">
                        <label>INTERVALO DATOS (SEG)</label>
                        <input type="number" id="inter" step="0.1" value="1.0">
                    </div>
                    
                    <button id="btnSave" class="action-btn" onclick="save(event)">APLICAR CAMBIOS</button>
                </div>
            </div>
            
            <!-- Right Panel -->
            <div class="column">
                <!-- Monitor -->
                <div class="panel" id="panel_monitor" style="flex: 1.2; min-height: 0;">
                    <h2><span class="dot" style="background:#0a5da7; box-shadow: 0 0 10px #0a5da7"></span> NIXIE MONITOR</h2>
                    <div class="display-peso" id="peso_txt">000.00</div>
                    <div class="led-container" id="led_cont"></div>
                    <div class="expand-btn-container">
                        <button id="btnPiP" class="expand-btn" onclick="openPiP()" style="margin-right: 10px;">
                            <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none"><rect x="2" y="3" width="20" height="14" rx="2"/><rect x="11" y="10" width="9" height="7" rx="1" fill="currentColor" opacity="0.3"/></svg>
                            PiP
                        </button>
                        <button id="btnExpandir" class="expand-btn" onclick="openFS()">
                            <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>
                            EXPANDIR VISOR
                        </button>
                    </div>
                </div>
                
                <!-- Logs Container -->
                <div class="grid-2" style="flex: 1; min-height: 0; overflow: hidden;">
                    <div class="panel keep-dark" style="padding: 0; border: 1px solid rgba(54,176,201,0.2); background: rgba(0,43,73,0.5); height: 100%;">
                        <div class="terminal">
                            <div class="terminal-header">
                                <span class="terminal-title">BÁSCULA_IO.sys</span>
                            </div>
                            <div class="log-box" id="log_bas"></div>
                        </div>
                    </div>
                    <div class="panel keep-dark" style="padding: 0; border: 1px solid rgba(54,176,201,0.2); background: rgba(0,43,73,0.5); height: 100%;">
                        <div class="terminal">
                            <div class="terminal-header">
                                <span class="terminal-title">SEMÁFORO_IO.sys</span>
                            </div>
                            <div class="log-box" id="log_sem" style="color: #36b0c9;"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Yahtzee Overlay -->
        <div id="yahtzee-overlay">
            <button id="game-close-btn" onclick="exitYahtzee()">[✕] ABORT SYSTEM</button>
            <h1 style="color: var(--nixie-glow-1); font-size: 2.5rem; text-shadow: var(--neon-shadow); margin-bottom: 15px; letter-spacing: 5px; font-weight: normal;">SYS.YAHTZEE // V.TOLE</h1>
            <div id="yz-board">
                <div id="yz-left">
                    <div id="yz-status">TU TURNO<br><span style="font-size:1.2rem; color:var(--text-main); opacity:0.8;">Inicia tirando</span></div>
                    <div id="yz-tole-avatar"></div>
                    <div class="yz-dice-container" id="yz-dice">
                        <div class="yz-die" id="yz-d0" onclick="toggleHold(0)">⚀</div>
                        <div class="yz-die" id="yz-d1" onclick="toggleHold(1)">⚀</div>
                        <div class="yz-die" id="yz-d2" onclick="toggleHold(2)">⚀</div>
                        <div class="yz-die" id="yz-d3" onclick="toggleHold(3)">⚀</div>
                        <div class="yz-die" id="yz-d4" onclick="toggleHold(4)">⚀</div>
                    </div>
                    <button class="yz-btn" id="yz-roll-btn" onclick="rollDiceClick()">[ LANZAR ]</button>
                    <div style="text-align:center; font-size:0.8rem; margin-top:10px; color:var(--text-main); opacity: 0.6;">CLICK TO LOCK DICE // 3 ROLLS MAX</div>
                </div>
                <div id="yz-right">
                    <table class="yz-table">
                        <thead>
                            <tr><th>CLASS</th><th>USR_01</th><th>A.I. TOLE</th></tr>
                        </thead>
                        <tbody id="yz-tbody">
                            <!-- Filled dynamically -->
                        </tbody>
                        <tfoot>
                            <tr><th>SYS_TOTAL</th><th id="yz-total-p1">0</th><th id="yz-total-p2">0</th></tr>
                        </tfoot>
                    </table>
                </div>
            </div>
        </div>

        <script>
            let queue = []; let isRunning = false; let lastId = -1; let firstTick = true;
            
            function openFS() { 
                document.getElementById('panel_monitor').classList.add('fullscreen-mode'); 
                document.getElementById('exitBtn').style.display = 'block'; 
                document.getElementById('btnExpandir').style.display = 'none'; 
            }
            
            function closeFS() { 
                document.getElementById('panel_monitor').classList.remove('fullscreen-mode'); 
                document.getElementById('exitBtn').style.display = 'none'; 
                document.getElementById('btnExpandir').style.display = 'flex'; 
            }
            
            // --- PiP (Document Picture-in-Picture API) ---
            let pipWin = null;
            let pipPesoEl = null;
            let pipLedContainer = null;
            let pipQueue = []; let pipIsRunning = false;
            
            async function openPiP() {
                if (!('documentPictureInPicture' in window)) {
                    alert('Tu navegador no soporta Document PiP. Usa Chrome 116+ o Edge 116+.');
                    return;
                }
                if (pipWin) { pipWin.focus(); return; }
                
                pipWin = await documentPictureInPicture.requestWindow({ width: 520, height: 280 });
                
                // Inject styles into PiP window
                const style = pipWin.document.createElement('style');
                style.textContent = `
                    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=VT323&display=swap');
                    * { box-sizing: border-box; margin: 0; padding: 0; }
                    body {
                        background: #010b14; overflow: hidden; display: flex; flex-direction: column;
                        height: 100vh; padding: 12px; font-family: 'Share Tech Mono', monospace;
                    }
                    #pip-peso {
                        font-family: 'VT323', monospace; font-size: 1.6em; text-align: center;
                        color: #ffffff; text-shadow: 0 0 5px #fff, 0 0 10px #36b0c9, 0 0 20px #0a5da7;
                        letter-spacing: 5px; flex-shrink: 0; margin-bottom: 8px; line-height: 1;
                        padding: 6px; background: rgba(0,0,0,0.5); border-radius: 10px;
                    }
                    #pip-led {
                        background: rgba(2,6,12,0.9); border: 1px solid rgba(255,255,255,0.05);
                        flex-grow: 1; min-height: 0; overflow: hidden; position: relative;
                        display: flex; align-items: center; border-radius: 16px;
                        box-shadow: inset 0 0 20px rgba(0,0,0,1);
                    }
                    .pip-led-text {
                        white-space: nowrap; position: absolute; font-family: 'VT323', monospace;
                        font-size: clamp(3rem, 15vh, 6rem); font-weight: normal; left: 100%;
                        will-change: transform; color: #ffffff;
                        text-shadow: 0 0 5px #fff, 0 0 10px #36b0c9, 0 0 20px #0a5da7, 0 0 40px #002b49;
                        letter-spacing: 4px; z-index: 1;
                    }
                    @keyframes marquee { 0% { left: 100%; transform: translateX(0); } 100% { left: 0%; transform: translateX(-100%); } }
                `;
                pipWin.document.head.appendChild(style);
                pipWin.document.title = 'NIXIE PiP';
                
                // Build content
                pipWin.document.body.innerHTML = '<div id="pip-peso">000.00</div><div id="pip-led"></div>';
                pipPesoEl = pipWin.document.getElementById('pip-peso');
                pipLedContainer = pipWin.document.getElementById('pip-led');
                
                // Clean up on close
                pipWin.addEventListener('pagehide', () => {
                    pipWin = null; pipPesoEl = null; pipLedContainer = null;
                    pipQueue = []; pipIsRunning = false;
                });
            }
            
            function closePiP() {
                if (pipWin) { pipWin.close(); pipWin = null; pipPesoEl = null; pipLedContainer = null; }
            }
            
            // PiP marquee queue
            function pipPlayQueue() {
                if (pipIsRunning || pipQueue.length === 0 || !pipLedContainer) return;
                pipIsRunning = true;
                const m = pipQueue.shift();
                const span = pipWin.document.createElement('span');
                span.className = 'pip-led-text';
                let baseColor = m.color === 'white' ? '#FFFFFF' : m.color;
                span.style.color = '#FFFFFF';
                span.style.textShadow = '0 0 5px #FFFFFF, 0 0 10px ' + baseColor + ', 0 0 20px ' + baseColor + ', 0 0 40px ' + baseColor;
                span.innerText = m.text || " ";
                pipLedContainer.innerHTML = '';
                pipLedContainer.appendChild(span);
                let dur = Math.max(4.0, (m.text || " ").length * 0.25);
                span.style.animation = 'marquee ' + dur + 's linear forwards';
                let to;
                const onEnd = () => { if(to) clearTimeout(to); pipIsRunning = false; setTimeout(pipPlayQueue, 150); };
                span.addEventListener('animationend', onEnd);
                to = setTimeout(onEnd, (dur * 1000) + 1200);
            }
            
            document.addEventListener('keydown', (e) => { 
                if (e.key === 'Escape') {
                    if (document.getElementById('panel_monitor').classList.contains('fullscreen-mode')) closeFS();
                }
            });
            
            function updateUI() {
                const m = document.getElementById('modo').value;
                document.getElementById('ui-manual').classList.toggle('hidden', m === 'auto');
                document.getElementById('ui-auto').classList.toggle('hidden', m === 'manual');
            }
            
            function createConfetti(x, y) {
                for (let i = 0; i < 40; i++) {
                    const conf = document.createElement('div');
                    conf.className = 'confetti';
                    conf.style.left = x + 'px';
                    conf.style.top = y + 'px';
                    const angle = Math.random() * Math.PI * 2;
                    const velocity = 100 + Math.random() * 200;
                    const vx = Math.cos(angle) * velocity;
                    const vy = Math.sin(angle) * velocity - 100;
                    document.body.appendChild(conf);
                    
                    conf.getBoundingClientRect(); // reflow
                    
                    conf.style.transition = `transform 1s cubic-bezier(0.25, 1, 0.5, 1), opacity 1s ease-in`;
                    conf.style.transform = `translate(${vx}px, ${vy}px) rotate(${Math.random() * 720}deg) scale(${Math.random() * 0.8 + 0.4})`;
                    conf.style.opacity = '0';
                    setTimeout(() => conf.remove(), 1000);
                }
            }
            
            async function save(e) {
                const btn = document.getElementById('btnSave');
                const rect = btn.getBoundingClientRect();
                createConfetti(rect.left + rect.width/2, rect.top + rect.height/2);
                
                let modo = document.getElementById('modo').value;
                let manual_val = parseInt(document.getElementById('manual').value);
                
                if (modo === 'manual' && manual_val === 666) {
                    const img = document.getElementById('toleImg');
                    img.style.display = 'block';
                    img.style.animation = 'pulse 0.1s infinite alternate';
                    setTimeout(() => { img.style.display = 'none'; img.style.animation = ''; }, 800);
                }

                if (modo === 'manual' && manual_val === 777) {
                    startYahtzee();
                    return; // Interceptar
                }
                
                let min = parseInt(document.getElementById('rmin').value);
                let max = parseInt(document.getElementById('rmax').value);
                if (modo === 'auto' && min > max) {
                    alert('ERROR: El mínimo no puede ser mayor al máximo.');
                    return;
                }
                
                btn.style.transform = 'scale(0.95)';
                setTimeout(() => { btn.style.transform = ''; }, 100);
                
                const p = { modo: modo, valor_manual: manual_val, rango: [min, max], intervalo_bascula: parseFloat(document.getElementById('inter').value) };
                const res = await fetch('/config', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(p) });
                
                if(res.ok) {
                    btn.innerText = ">> GUARDADO <<"; 
                    btn.style.borderColor = "#FFF";
                    btn.style.textShadow = "0 0 10px #FFF, 0 0 20px #36b0c9";
                    setTimeout(() => { 
                        btn.innerText = "APLICAR CAMBIOS"; 
                        btn.style.borderColor = ""; 
                        btn.style.textShadow = ""; 
                    }, 2000);
                }
            }
            
            async function tick() {
                try {
                    const res = await fetch('/status'); 
                    const d = await res.json();
                    
                    document.getElementById('peso_txt').innerText = d.peso_visual;
                    
                    // Update PiP peso
                    if (pipWin && pipPesoEl) {
                        pipPesoEl.innerText = d.peso_visual;
                    }
                    
                    let lb = document.getElementById('log_bas');
                    let ls = document.getElementById('log_sem');
                    let autoScrollBas = (lb.scrollTop + lb.clientHeight) >= (lb.scrollHeight - 20);
                    let autoScrollSem = (ls.scrollTop + ls.clientHeight) >= (ls.scrollHeight - 20);
                    
                    lb.innerHTML = d.logs_bas.join('<br>');
                    
                    // Modificar los logs del semáforo para darle un extra de retro
                    ls.innerHTML = d.logs_sem.map(x => x.replace('RX', '>> RX')).join('<br>');
                    
                    if (autoScrollBas) lb.scrollTop = lb.scrollHeight;
                    if (autoScrollSem) ls.scrollTop = ls.scrollHeight;
                    
                    if (firstTick) { 
                        firstTick = false; 
                        lastId = d.historial_semaforo && d.historial_semaforo.length > 0 ? d.historial_semaforo[d.historial_semaforo.length-1].id : -1; 
                        if (d.config) {
                            document.getElementById('modo').value = d.config.modo;
                            document.getElementById('manual').value = d.config.valor_manual;
                            document.getElementById('rmin').value = d.config.rango[0];
                            document.getElementById('rmax').value = d.config.rango[1];
                            document.getElementById('inter').value = d.config.intervalo_bascula;
                            updateUI();
                        }
                    } else if (d.historial_semaforo) {
                        let currentIds = d.historial_semaforo.map(x => x.id);
                        if (currentIds.length > 0 && lastId > Math.max(...currentIds)) { lastId = -1; }
                        d.historial_semaforo.forEach(m => {
                            if (m.id > lastId && m.text !== "") {
                                queue.push({ text: m.text, color: m.color });
                                if (pipWin) pipQueue.push({ text: m.text, color: m.color });
                                lastId = m.id;
                            }
                        });
                        playQueue();
                        if (pipWin) pipPlayQueue();
                    }
                } catch(e) {}
                setTimeout(tick, 500);
            }
            
            function playQueue() {
                try {
                    if (isRunning || queue.length === 0) return;
                    isRunning = true; 
                    const m = queue.shift(); 
                    const container = document.getElementById('led_cont');
                    
                    const span = document.createElement('span'); 
                    span.className = 'led-text'; 
                    // Simulamos el color nixie glow overriding the raw hex
                    let baseColor = m.color === 'white' ? '#FFFFFF' : m.color; 
                    span.style.color = '#FFFFFF';
                    span.style.textShadow = `0 0 5px #FFFFFF, 0 0 10px ${baseColor}, 0 0 20px ${baseColor}, 0 0 40px ${baseColor}`;
                    span.innerText = m.text || " ";
                    
                    container.innerHTML = ''; 
                    container.appendChild(span);
                    
                    let dur = Math.max(4.0, (m.text || " ").length * 0.25);
                    if (document.getElementById('panel_monitor').classList.contains('fullscreen-mode')) { dur *= 1.4; }
                    
                    span.style.animation = 'marquee ' + dur + 's linear forwards';
                    
                    let fsTimeout;
                    const onEnd = () => { 
                        if (fsTimeout) clearTimeout(fsTimeout); 
                        if (isRunning) { 
                            isRunning = false; 
                            setTimeout(playQueue, 150); 
                        } 
                    };
                    span.addEventListener('animationend', onEnd);
                    fsTimeout = setTimeout(onEnd, (dur * 1000) + 1200);
                } catch(e) { 
                    isRunning = false; 
                    setTimeout(playQueue, 500); 
                }
            }
            
            document.head.insertAdjacentHTML('beforeend', `<style>@keyframes pulse { 0% { transform: translate(-50%, -50%) scale(1); filter: sepia(100%) hue-rotate(-45deg) saturate(500%) contrast(1.5); box-shadow: 0 0 80px 20px rgba(255,0,0,0.8); } 50% { transform: translate(-50%, -50%) scale(1.1); filter: sepia(100%) hue-rotate(-60deg) saturate(600%) contrast(2); box-shadow: 0 0 150px 30px rgba(255,0,0,1); } 100% { transform: translate(-50%, -50%) scale(1); filter: sepia(100%) hue-rotate(-45deg) saturate(500%) contrast(1.5); box-shadow: 0 0 80px 20px rgba(255,0,0,0.8); } }</style>`);
            
            // --- LÓGICA SYS.YAHTZEE ---
            let yzState = { turnId: 0, rollsLeft: 3, diceObj: [1,1,1,1,1], held: [false,false,false,false,false], score: { 0: {}, 1: {} }, round: 1 };
            const YZ_CATS = [
                {id: '1s', name: 'UNOS (1)'}, {id: '2s', name: 'DOS (2)'}, {id: '3s', name: 'TRES (3)'},
                {id: '4s', name: 'CUATROS (4)'}, {id: '5s', name: 'CINCOS (5)'}, {id: '6s', name: 'SEIS (6)'},
                {id: '3k', name: '3-OF-A-KIND'}, {id: '4k', name: '4-OF-A-KIND'}, {id: 'fh', name: 'FULL_HOUSE'},
                {id: 'sm', name: 'SM_STRAIGHT'}, {id: 'lg', name: 'LG_STRAIGHT'}, {id: 'ya', name: 'YAHTZEE'},
                {id: 'ch', name: 'CHANCE_RND'}
            ];
            const diceChars = ['','⚀','⚁','⚂','⚃','⚄','⚅'];
            
            function startYahtzee() {
                document.getElementById('yahtzee-overlay').style.display = 'flex';
                document.getElementById('yz-tole-avatar').classList.remove('evil-tole');
                yzState = { turnId: 0, rollsLeft: 3, diceObj: [1,1,1,1,1], held: [false,false,false,false,false], score: {0:{}, 1:{}}, round: 1 };
                renderYzBoard();
                for(let i=0; i<5; i++) {
                    document.getElementById('yz-d'+i).className = 'yz-die';
                    document.getElementById('yz-d'+i).innerText = '⚀';
                }
                updateYzStatus("USR_01 TURNO<br><span style='font-size:1.2rem; color:var(--text-main); opacity:0.8;'>Waiting for throw...</span>");
                document.getElementById('yz-roll-btn').disabled = false;
            }
            function exitYahtzee() {
                document.getElementById('yahtzee-overlay').style.display = 'none';
            }
            function renderYzBoard() {
                let html = '';
                YZ_CATS.forEach(c => {
                    let s0 = yzState.score[0][c.id]; let v0 = s0 !== undefined ? s0 : '';
                    let s1 = yzState.score[1][c.id]; let v1 = s1 !== undefined ? s1 : '';
                    let cl0 = s0 !== undefined ? 'filled' : 'active-p0';
                    let cl1 = s1 !== undefined ? 'filled' : '';
                    html += `<tr><td>${c.name}</td>
                             <td class="yz-score-cell ${cl0}" id="yz-c-0-${c.id}" onclick="scoreCat('${c.id}',0)" data-preview="">${v0}</td>
                             <td class="yz-score-cell ${cl1}" id="yz-c-1-${c.id}">${v1}</td></tr>`;
                });
                document.getElementById('yz-tbody').innerHTML = html;
                document.getElementById('yz-total-p1').innerText = calcTotal(0);
                document.getElementById('yz-total-p2').innerText = calcTotal(1);
            }
            function calcTotal(p) {
                let sum = 0; let upperSum = 0;
                for(let k in yzState.score[p]) {
                    sum += yzState.score[p][k];
                    if(['1s','2s','3s','4s','5s','6s'].includes(k)) upperSum += yzState.score[p][k];
                }
                if(upperSum >= 63) sum += 35; // upper bonus
                return sum;
            }
            function toggleHold(idx) {
                if(yzState.turnId !== 0 || yzState.rollsLeft === 3) return; 
                yzState.held[idx] = !yzState.held[idx];
                document.getElementById('yz-d'+idx).className = 'yz-die' + (yzState.held[idx] ? ' held' : '');
            }
            function rollDiceClick() {
                if(yzState.turnId !== 0 || yzState.rollsLeft <= 0) return;
                rollTheDice();
            }
            function rollTheDice() {
                for(let i=0; i<5; i++) {
                    if(!yzState.held[i]) {
                        yzState.diceObj[i] = Math.floor(Math.random() * 6) + 1;
                        document.getElementById('yz-d'+i).innerText = diceChars[yzState.diceObj[i]];
                        let el = document.getElementById('yz-d'+i);
                        el.style.transform = 'scale(0.8) rotate('+(Math.random()*360)+'deg)';
                        setTimeout(()=>el.style.transform = yzState.held[i]?'translateY(4px)':'', 250);
                    }
                }
                yzState.rollsLeft--;
                if (yzState.turnId === 0) {
                    updateYzStatus(`USR_01 TURNO<br><span style='font-size:1.2rem; color:var(--text-main); opacity:0.8;'>TRIES LEFT: ${yzState.rollsLeft}</span>`);
                    if(yzState.rollsLeft <= 0) {
                        document.getElementById('yz-roll-btn').disabled = true;
                        updateYzStatus("SYS.WAITING_INPUT<br><span style='font-size:1.2rem; color:var(--brand-cyan); opacity:0.8;'>SELECT A CATEGORY (TÚ)</span>");
                    }
                    updatePreviews();
                } else {
                    updateYzStatus(`A.I. CALC<br><span style='font-size:1.2rem; color:var(--brand-cyan); opacity:0.8;'>Processing... [${yzState.rollsLeft}]</span>`);
                }
            }
            function updateYzStatus(txt) {
                document.getElementById('yz-status').innerHTML = txt;
            }
            function updatePreviews() {
                let opts = yzState.rollsLeft < 3 ? calcScoreOptions(yzState.diceObj) : {};
                YZ_CATS.forEach(c => {
                    let cell = document.getElementById('yz-c-0-'+c.id);
                    if(cell && !cell.classList.contains('filled')) {
                        cell.setAttribute('data-preview', opts[c.id] !== undefined ? opts[c.id] : '');
                    }
                });
            }
            function calcScoreOptions(dice) {
                let counts = {1:0, 2:0, 3:0, 4:0, 5:0, 6:0};
                let sum = 0;
                dice.forEach(d => { counts[d]++; sum += d; });
                let res = { '1s': counts[1]*1, '2s': counts[2]*2, '3s': counts[3]*3, '4s': counts[4]*4, '5s': counts[5]*5, '6s': counts[6]*6, '3k': 0, '4k': 0, 'fh': 0, 'sm': 0, 'lg': 0, 'ya': 0, 'ch': sum };
                let has3 = false; let has2 = false;
                for(let i=1; i<=6; i++) {
                    if(counts[i] >= 3) { res['3k'] = sum; has3 = true; }
                    if(counts[i] >= 4) res['4k'] = sum;
                    if(counts[i] === 5) res['ya'] = 50;
                    if(counts[i] === 2) has2 = true;
                }
                if((has3 && has2) || res['ya']===50) res['fh'] = 25;
                const str = Array.from(new Set(dice)).sort().join('');
                if(str.includes('1234') || str.includes('2345') || str.includes('3456')) res['sm'] = 30;
                if(str.includes('12345') || str.includes('23456')) res['lg'] = 40;
                return res;
            }
            function scoreCat(catId, pId) {
                if(yzState.turnId !== pId || yzState.rollsLeft === 3) return;
                if(yzState.score[pId][catId] !== undefined) return;
                
                let opts = calcScoreOptions(yzState.diceObj);
                yzState.score[pId][catId] = opts[catId] || 0;
                
                yzState.held = [false,false,false,false,false];
                for(let i=0; i<5; i++) document.getElementById('yz-d'+i).className = 'yz-die';
                renderYzBoard();
                
                if(pId === 0) {
                    yzState.turnId = 1;
                    yzState.rollsLeft = 3;
                    document.getElementById('yz-roll-btn').disabled = true;
                    updateYzStatus("A.I. ACTIVE");
                    setTimeout(toleTurn, 1000);
                } else {
                    yzState.turnId = 0;
                    yzState.rollsLeft = 3;
                    yzState.round++;
                    if(yzState.round > 13) {
                        let t1 = calcTotal(0); let t2 = calcTotal(1);
                        let w = t1 > t2 ? 'USR_01 WINS' : (t2>t1 ? 'A.I. WINS' : 'TIE DETECTED');
                        updateYzStatus(`SYS.HALTED<br><span style='font-size:1.5rem;'>[ ${w} ]</span>`);
                        if (t1 > t2) {
                            for(let k=0; k<8; k++) setTimeout(()=>createConfetti(window.innerWidth/2, window.innerHeight/3), k*300);
                        } else if (t2 > t1) {
                            document.getElementById('yz-tole-avatar').classList.add('evil-tole');
                        }
                    } else {
                        updateYzStatus(`USR_01 TURNO<br><span style='font-size:1.2rem; color:var(--text-main); opacity:0.8;'>Round ${yzState.round}/13</span>`);
                        document.getElementById('yz-roll-btn').disabled = false;
                    }
                }
            }
            function toleTurn() {
                if(yzState.turnId !== 1 || yzState.round > 13) return;
                rollTheDice();
                
                let decidedCat = null;
                if(yzState.rollsLeft > 0) {
                    let counts = {1:0, 2:0, 3:0, 4:0, 5:0, 6:0};
                    yzState.diceObj.forEach(d => counts[d]++);
                    let maxCount = 0; let valWithMax = 0;
                    for(let i=1;i<=6;i++) { if(counts[i]>maxCount){maxCount=counts[i]; valWithMax=i;} }
                    
                    let opts = calcScoreOptions(yzState.diceObj);
                    
                    if(maxCount >= 4 && yzState.score[1]['ya'] === undefined) {
                        for(let i=0; i<5; i++) yzState.held[i] = yzState.diceObj[i] === valWithMax;
                    } else if (maxCount === 3 && yzState.score[1]['4k'] === undefined) {
                        for(let i=0; i<5; i++) yzState.held[i] = yzState.diceObj[i] === valWithMax;
                    } else if (opts['lg'] === 40 && yzState.score[1]['lg'] === undefined) {
                        decidedCat = 'lg';
                    } else if (opts['sm'] === 30 && yzState.score[1]['sm'] === undefined && yzState.score[1]['lg'] === undefined) {
                        let seen = [];
                        for(let i=0; i<5; i++) {
                            if(!seen.includes(yzState.diceObj[i])) { yzState.held[i] = true; seen.push(yzState.diceObj[i]); }
                        }
                    } else if (maxCount >= 2) {
                        for(let i=0; i<5; i++) yzState.held[i] = yzState.diceObj[i] === valWithMax;
                    } else {
                        yzState.held = [false,false,false,false,false];
                    }
                    
                    for(let i=0; i<5; i++) document.getElementById('yz-d'+i).className = 'yz-die' + (yzState.held[i] ? ' held' : '');
                    
                    if(decidedCat) {
                        setTimeout(()=>scoreCat(decidedCat, 1), 1500);
                        return;
                    }
                    setTimeout(toleTurn, 1500);
                } else {
                    let opts = calcScoreOptions(yzState.diceObj);
                    let prefs = ['ya','lg','sm','fh','4k','3k','6s','5s','4s','3s','2s','1s','ch'];
                    let picked = null;
                    for(let c of prefs) {
                        if(yzState.score[1][c] === undefined && opts[c] > 0) { picked = c; break; }
                    }
                    if(!picked) {
                        let sacrifices = ['1s','2s','3s','ya','lg','sm','fh','4k','3k','ch','4s','5s','6s'];
                        for(let c of sacrifices) {
                            if(yzState.score[1][c] === undefined) { picked = c; break; }
                        }
                    }
                    setTimeout(()=>scoreCat(picked, 1), 1500);
                }
            }

            tick();
        </script>
    </body>
    </html>
"""
    return HTMLResponse(content=content)

@app.get("/logo")
def get_logo():
    img_path = os.path.join(os.path.dirname(__file__), "becker-lasec-logo-gris.png")
    if os.path.exists(img_path):
        return FileResponse(img_path)
    return HTMLResponse("")

@app.get("/tole.webp")
def get_tole():
    img_path = os.path.join(os.path.dirname(__file__), "tole.webp")
    if os.path.exists(img_path):
        return FileResponse(img_path)
    return HTMLResponse("")

@app.get("/status")
def get_status():
    return {"peso_visual": f"{(peso_actual * 100) / 100:06.2f}", "historial_semaforo": historial_semaforo, "logs_bas": logs_bascula, "logs_sem": logs_semaforo, "config": config}

@app.post("/config")
async def set_config(request: Request):
    global config
    data = await request.json()
    if data["rango"][0] > data["rango"][1]: data["rango"][0] = data["rango"][1]
    config = data
    return {"status": "ok"}

# --- BÁSCULA MULTICLIENTE ---
def atender_cliente_bascula(conn, addr):
    global peso_actual
    try:
        with conn:
            while True:
                p = random.randint(config["rango"][0], config["rango"][1]) if config["modo"] == "auto" else config["valor_manual"]
                peso_actual = p
                conn.sendall(f"\x02+{p/100:06.2f} tons\r\n".encode('ascii'))
                añadir_log(logs_bascula, f"TX({addr[0][-2:]}) -> {p/100:06.2f}")
                time.sleep(config.get("intervalo_bascula", 1.0))
    except: pass

def server_bascula():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", BASCULA_PORT))
    s.listen(10)
    while True:
        try:
            conn, addr = s.accept()
            threading.Thread(target=atender_cliente_bascula, args=(conn, addr), daemon=True).start()
        except: pass

# --- SEMÁFORO MULTICLIENTE ---
def atender_cliente_semaforo(conn, addr):
    global historial_semaforo, msg_id_counter
    try:
        with conn:
            añadir_log(logs_semaforo, f"DEBUG: Conexión de {addr[0]}")
            while True:
                data = conn.recv(8192)
                if not data:
                    break
                raw = data.decode('utf-8', errors='ignore').strip().replace('}{', '}\n{')
                añadir_log(logs_semaforo, f"DEBUG: Recibido len={len(raw)}")
                
                for line in raw.split('\n'):
                    if not line.strip().startswith('{'): 
                        continue
                    try:
                        msg_json = json.loads(line)
                        m_text = msg_json.get('Text', '')
                        m_color = {0:"white", 1:"#ff5555", 2:"#0a5da7", 3:"#50fa7b", 4:"#bd93f9", 5:"#0a5da7", 6:"#f1fa8c", 7:"#ff79c6"}.get(msg_json.get('Color', 0), "white")
                        if m_text:
                            m_text_str = str(m_text)
                            msg_id_counter += 1
                            historial_semaforo.append({"text": m_text_str.upper(), "color": m_color, "id": msg_id_counter})
                            if len(historial_semaforo) > 100: historial_semaforo.pop(0)
                            añadir_log(logs_semaforo, f"RX({addr[0][-2:]}): {m_text_str}")
                        else:
                            añadir_log(logs_semaforo, f"DEBUG: JSON sin 'Text'")
                    except Exception as e:
                        añadir_log(logs_semaforo, f"DEBUG: Error JSON -> {str(e)}")
                
                try:
                    conn.sendall(b"OK\n")
                except Exception as e:
                    añadir_log(logs_semaforo, f"DEBUG: Error enviando OK -> {str(e)}")
                    break
    except Exception as e:
        añadir_log(logs_semaforo, f"DEBUG: Crash socket -> {str(e)}")

def server_semaforo():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", SEMAFORO_PORT))
    s.listen(10)
    while True:
        try:
            conn, addr = s.accept()
            threading.Thread(target=atender_cliente_semaforo, args=(conn, addr), daemon=True).start()
        except: pass

if __name__ == "__main__":
    threading.Thread(target=server_bascula, daemon=True).start()
    threading.Thread(target=server_semaforo, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=WEB_PORT, log_level="error")