import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Oráculo Multi-Zona", page_icon="🎣", layout="wide")

# --- 1. BASE DE DATOS DE ZONAS (COORDENADAS EXACTAS) ---
ZONAS = {
    "El Saler":           {"lat": 39.37, "lon": -0.25},
    "Pinedo":             {"lat": 39.42, "lon": -0.33},
    "Marina (Malvarrosa)":{"lat": 39.47, "lon": -0.32},
    "Alboraya":           {"lat": 39.50, "lon": -0.31},
    "Faro de Cullera":    {"lat": 39.18, "lon": -0.22} 
}

# Coordenada FIJA para la marea (Usamos la boya de Valencia que nunca falla)
# La marea es igual en toda la costa, así aseguramos que no haya errores de "tierra"
LAT_MAREA_REF = 39.40 
LON_MAREA_REF = -0.20

# --- FUNCIONES ---
def obtener_datos(lat, lon, fecha_str):
    try:
        # Clima y Olas (Específico de la zona elegida)
        url_clima = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=wind_speed_10m,wind_direction_10m&timezone=Europe%2FMadrid&start_date={fecha_str}&end_date={fecha_str}"
        url_olas = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&hourly=wave_height&timezone=Europe%2FMadrid&start_date={fecha_str}&end_date={fecha_str}"
        
        # Marea (General de la costa)
        url_marea = f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT_MAREA_REF}&longitude={LON_MAREA_REF}&hourly=tide_height&timezone=Europe%2FMadrid&start_date={fecha_str}&end_date={fecha_str}"
        
        return requests.get(url_clima).json(), requests.get(url_olas).json(), requests.get(url_marea).json()
    except:
        return None, None, None

def calcular_direccion(grados):
    if 45 <= grados <= 135: return "Levante (E)"
    elif 225 <= grados <= 315: return "Poniente (O)"
    return "Var."

# --- INTERFAZ ---
st.title("🎣 Oráculo de Pesca: Comunidad Valenciana")
st.markdown("Previsión inteligente multizona.")

# --- SELECTORES ---
col1, col2, col3 = st.columns(3)

with col1:
    # AQUÍ ESTÁ LA NOVEDAD: EL SELECTOR DE ZONA
    zona_nombre = st.selectbox("📍 ¿Dónde vamos hoy?", list(ZONAS.keys()))
    
with col2:
    fecha = st.date_input("📅 Día:", datetime.now())
    
with col3:
    horas = st.slider("🕒 Horas:", 0, 23, (6, 12))

# Recuperamos las coordenadas de la zona elegida
lat_zona = ZONAS[zona_nombre]["lat"]
lon_zona = ZONAS[zona_nombre]["lon"]

if st.button(f"🚀 VER PREVISIÓN PARA {zona_nombre.upper()}"):
    fecha_str = fecha.strftime('%Y-%m-%d')
    
    with st.spinner(f'Analizando satélites sobre {zona_nombre}...'):
        # Pasamos las coordenadas de la zona elegida a la función
        clima, olas_data, marea = obtener_datos(lat_zona, lon_zona, fecha_str)
        
        if not clima or not olas_data:
            st.error("Error de conexión con el satélite.")
            st.stop()

        tides = [0]*24
        if marea and 'hourly' in marea:
            tides = marea['hourly']['tide_height']

        resultados = []
        
        for h in range(horas[0], horas[1] + 1):
            if h >= 24: break
            
            try:
                v_vel = clima['hourly']['wind_speed_10m'][h]
                v_dir = clima['hourly']['wind_direction_10m'][h]
                ola_h = olas_data['hourly']['wave_height'][h] if olas_data['hourly']['wave_height'][h] else 0.0
                marea_h = tides[h]
            except: continue

            dir_txt = calcular_direccion(v_dir)

            # LÓGICA DE CLARIDAD
            # Cullera tiene zonas de roca, pero la regla del agua clara sirve igual
            if ola_h > 0.6 and "Levante" in dir_txt: agua = "🟤 Turbia"
            elif "Poniente" in dir_txt or ola_h < 0.3: agua = "🔵 Clara"
            else: agua = "⚪ Variable"

            # ESTADO MAR
            if ola_h >= 0.4: estado_mar = "🌊 Agitado"
            else: estado_mar = "💎 Planchado"

            # MAREA
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

            # TIPO PLAYA (La lógica sirve para playas de arena)
            if marea_h >= 0.6: tipo_playa = "🌊 CORTA (Alta)"
            else: tipo_playa = "🏖️ LARGA (Baja)"

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

        # Mostrar Tabla
        st.dataframe(pd.DataFrame(resultados), use_container_width=True, hide_index=True)

        # Mapa pequeño para confirmar ubicación
        st.map(pd.DataFrame({'lat': [lat_zona], 'lon': [lon_zona]}), zoom=11)

        # Resumen
        st.info("""
        **ℹ️ NOTA ZONA:**
        * Los datos de **Viento y Olas** son exactos de **{}**.
        * La **Marea** es la general de Valencia (Válida para toda la costa).
        """.format(zona_nombre))
