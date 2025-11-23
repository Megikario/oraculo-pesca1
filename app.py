import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA (MODO ANCHO PARA QUE QUEPA LA TABLA) ---
st.set_page_config(page_title="Oráculo El Saler", page_icon="🎣", layout="wide")

# --- COORDENADAS (Las que funcionan) ---
LAT_PESCA = 39.37
LON_PESCA = -0.25
LAT_MAREA = 39.40   # Mar adentro (para que no falle la marea)
LON_MAREA = -0.20

# --- FUNCIONES ---
def obtener_datos(fecha_str):
    try:
        url_clima = f"https://api.open-meteo.com/v1/forecast?latitude={LAT_PESCA}&longitude={LON_PESCA}&hourly=wind_speed_10m,wind_direction_10m&timezone=Europe%2FMadrid&start_date={fecha_str}&end_date={fecha_str}"
        url_olas = f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT_PESCA}&longitude={LON_PESCA}&hourly=wave_height&timezone=Europe%2FMadrid&start_date={fecha_str}&end_date={fecha_str}"
        url_marea = f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT_MAREA}&longitude={LON_MAREA}&hourly=tide_height&timezone=Europe%2FMadrid&start_date={fecha_str}&end_date={fecha_str}"
        
        return requests.get(url_clima).json(), requests.get(url_olas).json(), requests.get(url_marea).json()
    except:
        return None, None, None

def calcular_direccion(grados):
    if 45 <= grados <= 135: return "Levante (E)"
    elif 225 <= grados <= 315: return "Poniente (O)"
    return "Var."

# --- INTERFAZ ---
st.title("🎣 Oráculo de Pesca: El Saler")
st.markdown("**Versión Colab:** Tabla completa con tipo de playa y valoración.")

col1, col2 = st.columns(2)
with col1:
    fecha = st.date_input("📅 Día de pesca:", datetime.now())
with col2:
    horas = st.slider("🕒 Horario:", 0, 23, (6, 12))

if st.button("🚀 GENERAR TABLA"):
    fecha_str = fecha.strftime('%Y-%m-%d')
    
    with st.spinner('Calculando mareas y vientos...'):
        clima, olas_data, marea = obtener_datos(fecha_str)
        
        if not clima or not olas_data:
            st.error("Error de conexión.")
            st.stop()

        # Datos seguros de marea
        tides = [0]*24
        if marea and 'hourly' in marea:
            tides = marea['hourly']['tide_height']

        resultados = []
        
        for h in range(horas[0], horas[1] + 1):
            if h >= 24: break
            
            # --- 1. DATOS BÁSICOS ---
            try:
                v_vel = clima['hourly']['wind_speed_10m'][h]
                v_dir = clima['hourly']['wind_direction_10m'][h]
                ola_h = olas_data['hourly']['wave_height'][h] if olas_data['hourly']['wave_height'][h] else 0.0
                marea_h = tides[h]
            except: continue

            dir_txt = calcular_direccion(v_dir)

            # --- 2. LÓGICA DE NEGOCIO (TUS REGLAS) ---
            
            # A) Claridad
            if ola_h > 0.6 and "Levante" in dir_txt: agua = "🟤 Turbia"
            elif "Poniente" in dir_txt or ola_h < 0.3: agua = "🔵 Clara"
            else: agua = "⚪ Variable"

            # B) Estado del Mar (Agitado vs Planchado)
            if ola_h >= 0.4: estado_mar = "🌊 Agitado"
            else: estado_mar = "💎 Planchado"

            # C) Marea y Tipo de Playa
            # Calculamos tendencia
            prev = tides[h-1] if h > 0 else marea_h
            sig = tides[h+1] if h < 23 else marea_h
            
            if marea_h > prev and marea_h > sig: 
                tendencia = "🛑 PLEAMAR"
                val = "⛔ PARADA"
            elif marea_h < prev and marea_h < sig: 
                tendencia = "🛑 BAJAMAR"
                val = "⛔ PARADA"
            elif sig > marea_h: 
                tendencia = "⬆️ SUBIENDO"
                val = "✅ BUENA"
            else: 
                tendencia = "⬇️ BAJANDO"
                val = "⚠️ REGULAR"

            # Tipo de playa según altura (0.6m es el umbral aprox en El Saler)
            if marea_h >= 0.6: tipo_playa = "🌊 CORTA (Alta)"
            else: tipo_playa = "🏖️ LARGA (Baja)"

            # --- 3. GUARDAR FILA ---
            resultados.append({
                "HORA": f"{h}:00",
                "VIENTO": f"{v_vel} kmh {dir_txt}",
                "OLAS": f"{ola_h}m",
                "ESTADO MAR": estado_mar,
                "AGUA": agua,
                "TIPO PLAYA": tipo_playa,
                "MAREA": tendencia,
                "VAL.": val
            })

        # --- MOSTRAR TABLA ---
        df = pd.DataFrame(resultados)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # --- RESUMEN DEBAJO (IGUAL QUE EN COLAB) ---
        st.markdown("---")
        st.info("""
        **ℹ️ RESUMEN RÁPIDO:**
        * 🌊 **Agitado** + 🟤 **Turbia** = Pescado confiado (Entra a comer).
        * 💎 **Planchado** + 🔵 **Clara** = Pescado difícil (Hilo fino).
        * ✅ **BUENA (Subiendo):** El agua tapa la orilla (**Playa Corta**). Pesca CERCA.
        """)
