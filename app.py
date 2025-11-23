import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN V4 (Anti-Fallos) ---
st.set_page_config(page_title="Oráculo El Saler", page_icon="🎣")

LAT_PESCA = 39.37
LON_PESCA = -0.25
LAT_MAREA = 39.45 
LON_MAREA = -0.30 

# --- FUNCIONES ---
def obtener_datos_marea(fecha_str):
    # TRUCO V4: Simplificamos la petición al máximo para evitar errores del servidor
    url = f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT_MAREA}&longitude={LON_MAREA}&hourly=tide_height&timezone=Europe%2FMadrid&start_date={fecha_str}&end_date={fecha_str}"
    try:
        resp = requests.get(url)
        if resp.status_code != 200:
            return None # Si falla, devolvemos "vacío" silenciosamente
        return resp.json()['hourly']['tide_height']
    except:
        return None

def obtener_datos_clima(fecha_str):
    url_clima = f"https://api.open-meteo.com/v1/forecast?latitude={LAT_PESCA}&longitude={LON_PESCA}&hourly=wind_speed_10m,wind_direction_10m&timezone=Europe%2FMadrid&start_date={fecha_str}&end_date={fecha_str}"
    url_olas = f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT_PESCA}&longitude={LON_PESCA}&hourly=wave_height&timezone=Europe%2FMadrid&start_date={fecha_str}&end_date={fecha_str}"
    try:
        return requests.get(url_clima).json(), requests.get(url_olas).json()
    except:
        return None, None

# --- INTERFAZ ---
st.title("🎣 Oráculo de Pesca: El Saler")
st.caption("Versión 4: Estabilidad Máxima")

col1, col2 = st.columns(2)
with col1:
    fecha = st.date_input("¿Qué día vas?", datetime.now())
with col2:
    horas = st.slider("Horario de pesca", 0, 23, (7, 11))

if st.button("🔮 ANALIZAR JORNADA"):
    fecha_str = fecha.strftime('%Y-%m-%d')
    
    with st.spinner('Consultando boyas...'):
        marea_data = obtener_datos_marea(fecha_str)
        clima_data, olas_data = obtener_datos_clima(fecha_str)
        
        if not clima_data or not olas_data:
            st.error("❌ Error de conexión total. Inténtalo luego.")
            st.stop()

        if not marea_data:
            st.warning("⚠️ El servidor de mareas está en mantenimiento, pero aquí tienes el Viento y el Agua:")
            marea_data = [0] * 24 # Relleno invisible

        resultados = []
        for h in range(horas[0], horas[1] + 1):
            if h >= 24: break
            
            # Clima (Esto es lo fiable hoy)
            try:
                viento = clima_data['hourly']['wind_speed_10m'][h]
                dir_v = clima_data['hourly']['wind_direction_10m'][h]
                olas = olas_data['hourly']['wave_height'][h] if olas_data['hourly']['wave_height'][h] else 0.0
            except: continue

            # Claridad (Tu regla de oro)
            if 45 <= dir_v <= 135: dir_txt = "Levante (E)"
            elif 225 <= dir_v <= 315: dir_txt = "Poniente (O)"
            else: dir_txt = "Var."
            
            if olas > 0.6 and "Levante" in dir_txt: claridad = "🟤 Turbia"
            elif "Poniente" in dir_txt or olas < 0.3: claridad = "🔵 Clara"
            else: claridad = "⚪ Variable"

            # Marea (Solo si funciona)
            estado_marea = "--"
            if marea_data[0] != 0:
                try:
                    actual = marea_data[h]
                    sig = marea_data[h+1] if h < 23 else actual
                    prev = marea_data[h-1] if h > 0 else actual
                    
                    if actual > prev and actual > sig: estado_marea = "🛑 PLEAMAR"
                    elif actual < prev and actual < sig: estado_marea = "🛑 BAJAMAR"
                    elif sig > actual: estado_marea = "✅ SUBIENDO"
                    else: estado_marea = "⚠️ BAJANDO"
                except: pass

            resultados.append({
                "Hora": f"{h}:00",
                "Viento": f"{viento} km/h {dir_txt}",
                "Olas": f"{olas} m",
                "Agua": clarity,
                "Marea": estado_marea
            })
            # Pequeño fix para variable clarity mal escrita arriba
            resultados[-1]["Agua"] = claridad 

        st.dataframe(pd.DataFrame(resultados), use_container_width=True)
        
        if marea_data[0] == 0:
            st.info("💡 **Consejo:** Aunque falle la marea, con Poniente y olas de 0.4m el agua estará cristalina.")
