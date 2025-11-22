import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Oráculo El Saler", page_icon="🎣")

LAT_PESCA = 39.37
LON_PESCA = -0.25
LAT_MAREA = 39.45  # Puerto (datos seguros)
LON_MAREA = -0.30

# --- FUNCIONES ---
def obtener_datos_marea(fecha_str):
    url = f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT_MAREA}&longitude={LON_MAREA}&hourly=tide_height&timezone=Europe%2FMadrid&start_date={fecha_str}&end_date={fecha_str}"
    try:
        return requests.get(url).json()['hourly']['tide_height']
    except:
        return None

def obtener_datos_clima(fecha_str):
    url_clima = f"https://api.open-meteo.com/v1/forecast?latitude={LAT_PESCA}&longitude={LON_PESCA}&hourly=wind_speed_10m,wind_direction_10m&timezone=Europe%2FMadrid&start_date={fecha_str}&end_date={fecha_str}"
    url_olas = f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT_PESCA}&longitude={LON_PESCA}&hourly=wave_height&timezone=Europe%2FMadrid&start_date={fecha_str}&end_date={fecha_str}"
    
    clima = requests.get(url_clima).json()
    olas = requests.get(url_olas).json()
    return clima, olas

# --- INTERFAZ DE LA WEB ---
st.title("🎣 Oráculo de Pesca: El Saler")
st.markdown("Previsión inteligente de mareas, viento y claridad del agua.")

# Selectores (Calendario y Deslizador de horas)
col1, col2 = st.columns(2)
with col1:
    fecha = st.date_input("¿Qué día vas?", datetime.now())
with col2:
    horas = st.slider("Horario de pesca", 0, 23, (7, 11)) # Por defecto de 7 a 11

if st.button("🔮 ANALIZAR JORNADA"):
    fecha_str = fecha.strftime('%Y-%m-%d')
    
    with st.spinner('Consultando boyas y satélites...'):
        try:
            # Obtener datos
            marea_data = obtener_datos_marea(fecha_str)
            clima_data, olas_data = obtener_datos_clima(fecha_str)
            
            if not marea_data:
                st.error("Error conectando con la boya de mareas.")
                st.stop()

            # Preparar tabla de resultados
            resultados = []
            
            for h in range(horas[0], horas[1] + 1):
                viento = clima_data['hourly']['wind_speed_10m'][h]
                dir_v = clima_data['hourly']['wind_direction_10m'][h]
                olas = olas_data['hourly']['wave_height'][h]
                marea_hoy = marea_data[h]
                
                # Lógica Marea
                try:
                    marea_next = marea_data[h+1] if h < 23 else marea_data[h]
                    marea_prev = marea_data[h-1] if h > 0 else marea_data[h]
                    diff = marea_next - marea_hoy
                    
                    if marea_hoy > marea_prev and marea_hoy > marea_next:
                        estado = "👑 PLEAMAR"
                        icono = "⛔"
                    elif marea_hoy < marea_prev and marea_hoy < marea_next:
                        estado = "💀 BAJAMAR"
                        icono = "⛔"
                    elif diff > 0:
                        estado = "⬆️ SUBIENDO"
                        icono = "✅"
                    else:
                        estado = "⬇️ BAJANDO"
                        icono = "⚠️"
                except:
                    estado = "Calculando"
                    icono = "❓"

                # Lógica Claridad
                if 45 <= dir_v <= 135: dir_txt = "Levante"
                elif 225 <= dir_v <= 315: dir_txt = "Poniente"
                else: dir_txt = "N/S"
                
                if olas > 0.6 and dir_txt == "Levante": claridad = "🟤 Turbia"
                elif dir_txt == "Poniente" or olas < 0.3: claridad = "🔵 Clara"
                else: claridad = "⚪ Variable"

                resultados.append({
                    "Hora": f"{h}:00",
                    "Viento (km/h)": f"{viento} ({dir_txt})",
                    "Olas (m)": olas,
                    "Agua": claridad,
                    "Estado Marea": estado,
                    "¿Pescar?": icono
                })

            # Mostrar Datos
            df = pd.DataFrame(resultados)
            st.dataframe(df, use_container_width=True)
            
            # Consejos
            st.info("💡 **CONSEJO RÁPIDO:** Si la marea está SUBIENDO (✅), lanza cerca. Si está BAJANDO (⬇️), busca profundidad lejos.")
            
            # Mapa
            st.map(pd.DataFrame({'lat': [LAT_PESCA], 'lon': [LON_PESCA]}), zoom=12)

        except Exception as e:
            st.error(f"Algo falló: {e}")
