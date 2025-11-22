import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN V3 (Boya Indestructible) ---
st.set_page_config(page_title="Oráculo El Saler", page_icon="🎣")

# 1. Punto de PESCA (El Saler - para viento/olas)
LAT_PESCA = 39.37
LON_PESCA = -0.25

# 2. Punto de MAREA (Boya del Puerto - Profundidad segura)
# Usamos una coordenada muy probada para evitar errores de "tierra"
LAT_MAREA = 39.44
LON_MAREA = -0.30 

# --- FUNCIONES ---
def obtener_datos_marea(fecha_str):
    # Pedimos datos
    url = f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT_MAREA}&longitude={LON_MAREA}&hourly=tide_height&timezone=Europe%2FMadrid&start_date={fecha_str}&end_date={fecha_str}"
    try:
        resp = requests.get(url)
        if resp.status_code != 200:
            # Si falla, devolvemos el mensaje exacto del servidor para verlo
            st.error(f"⚠️ Error Boya Mareas: {resp.text}")
            return None
        return resp.json()['hourly']['tide_height']
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

def obtener_datos_clima(fecha_str):
    # API Meteorológica (Viento)
    url_clima = f"https://api.open-meteo.com/v1/forecast?latitude={LAT_PESCA}&longitude={LON_PESCA}&hourly=wind_speed_10m,wind_direction_10m&timezone=Europe%2FMadrid&start_date={fecha_str}&end_date={fecha_str}"
    # API Marina (Olas)
    url_olas = f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT_PESCA}&longitude={LON_PESCA}&hourly=wave_height&timezone=Europe%2FMadrid&start_date={fecha_str}&end_date={fecha_str}"
    
    try:
        clima = requests.get(url_clima).json()
        olas = requests.get(url_olas).json()
        return clima, olas
    except:
        return None, None

# --- INTERFAZ ---
st.title("🎣 Oráculo de Pesca: El Saler (V3)")
st.caption("Versión: Boya Puerto + Detector de Errores")

col1, col2 = st.columns(2)
with col1:
    # Usamos datetime.now() real. Si tu sistema está en 2025, saldrá 2025.
    fecha = st.date_input("¿Qué día vas?", datetime.now())
with col2:
    horas = st.slider("Horario de pesca", 0, 23, (7, 11))

if st.button("🔮 CONSULTAR ESTADO"):
    fecha_str = fecha.strftime('%Y-%m-%d')
    
    with st.spinner('Contactando con boyas...'):
        # 1. Cargar Datos
        marea_data = obtener_datos_marea(fecha_str)
        clima_data, olas_data = obtener_datos_clima(fecha_str)
        
        # 2. Comprobar si tenemos al menos clima
        if not clima_data or not olas_data:
            st.error("❌ Error total: No se pueden cargar datos de viento/olas.")
            st.stop()
            
        # Si falta marea, avisamos pero seguimos
        if not marea_data:
            st.warning("⚠️ No hay datos de MAREA (posible fallo del servidor), pero aquí tienes el viento y las olas:")
            marea_data = [0] * 24 # Rellenamos con ceros para que no falle el programa

        # 3. Procesar
        resultados = []
        for h in range(horas[0], horas[1] + 1):
            if h >= 24: break
            
            # Datos Clima
            try:
                viento = clima_data['hourly']['wind_speed_10m'][h]
                dir_v = clima_data['hourly']['wind_direction_10m'][h]
                olas = olas_data['hourly']['wave_height'][h] if olas_data['hourly']['wave_height'][h] else 0.0
            except:
                continue # Saltar hora si falla

            # Datos Marea (Lógica)
            estado_marea = "--"
            icono_marea = ""
            if marea_data[0] != 0: # Solo calculamos si hay datos reales
                try:
                    marea_hoy = marea_data[h]
                    marea_next = marea_data[h+1] if h < 23 else marea_data[h]
                    marea_prev = marea_data[h-1] if h > 0 else marea_data[h]
                    
                    if marea_hoy > marea_prev and marea_hoy > marea_next:
                        estado_marea = "PLEAMAR (Alta)"
                        icono_marea = "🛑"
                    elif marea_hoy < marea_prev and marea_hoy < marea_next:
                        estado_marea = "BAJAMAR (Baja)"
                        icono_marea = "🛑"
                    elif marea_next > marea_hoy:
                        estado_marea = "SUBIENDO"
                        icono_marea = "✅"
                    else:
                        estado_marea = "BAJANDO"
                        icono_marea = "⚠️"
                except:
                    pass

            # Lógica Claridad Agua
            if 45 <= dir_v <= 135: dir_txt = "Levante (E)"
            elif 225 <= dir_v <= 315: dir_txt = "Poniente (O)"
            else: dir_txt = "Var."
            
            if olas > 0.6 and "Levante" in dir_txt: claridad = "🟤 Turbia"
            elif "Poniente" in dir_txt or olas < 0.3: claridad = "🔵 Clara"
            else: claridad = "⚪ Variable"

            resultados.append({
                "Hora": f"{h}:00",
                "Viento": f"{viento} km/h {dir_txt}",
                "Olas": f"{olas} m",
                "Agua": claridad,
                "Estado Marea": estado_marea,
                "¿Ir?": icono_marea
            })

        st.dataframe(pd.DataFrame(resultados), use_container_width=True)
        if marea_data[0] != 0:
            st.success("✅ Datos cargados al 100%")
