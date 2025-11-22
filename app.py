import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURACIÓN V2 ---
st.set_page_config(page_title="Oráculo El Saler", page_icon="🎣")

# Coordenadas ajustadas (Más adentro del mar para evitar errores de "tierra")
LAT_PESCA = 39.37
LON_PESCA = -0.25
LAT_MAREA = 39.40   # <--- CAMBIO: Movido más al sur/este
LON_MAREA = -0.28   # <--- CAMBIO: Más adentro del mar

# --- FUNCIONES ---
def obtener_datos_marea(fecha_str):
    # Añadimos &daily=tide_height para asegurar consistencia si falla el horario
    url = f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT_MAREA}&longitude={LON_MAREA}&hourly=tide_height&timezone=Europe%2FMadrid&start_date={fecha_str}&end_date={fecha_str}"
    try:
        respuesta = requests.get(url)
        # Si la respuesta no es "OK" (200), lanzamos el error para verlo
        respuesta.raise_for_status()
        data = respuesta.json()
        
        # Verificación extra: ¿Existen los datos?
        if 'hourly' not in data or 'tide_height' not in data['hourly']:
            st.error(f"El satélite respondió pero sin datos de marea. Respuesta: {data}")
            return None
            
        return data['hourly']['tide_height']
    except Exception as e:
        st.error(f"Error técnico conectando al satélite: {e}")
        return None

def obtener_datos_clima(fecha_str):
    url_clima = f"https://api.open-meteo.com/v1/forecast?latitude={LAT_PESCA}&longitude={LON_PESCA}&hourly=wind_speed_10m,wind_direction_10m&timezone=Europe%2FMadrid&start_date={fecha_str}&end_date={fecha_str}"
    url_olas = f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT_PESCA}&longitude={LON_PESCA}&hourly=wave_height&timezone=Europe%2FMadrid&start_date={fecha_str}&end_date={fecha_str}"
    
    clima = requests.get(url_clima).json()
    olas = requests.get(url_olas).json()
    return clima, olas

# --- INTERFAZ ---
st.title("🎣 Oráculo de Pesca: El Saler")
st.markdown("Versión 2.0 - Coordenadas corregidas")

col1, col2 = st.columns(2)
with col1:
    fecha = st.date_input("¿Qué día vas?", datetime.now())
with col2:
    horas = st.slider("Horario de pesca", 0, 23, (7, 11))

if st.button("🔮 ANALIZAR JORNADA"):
    fecha_str = fecha.strftime('%Y-%m-%d')
    
    with st.spinner('Triangulando satélites...'):
        # 1. Obtener Marea
        marea_data = obtener_datos_marea(fecha_str)
        
        # Si falla la marea, paramos aquí para ver el error
        if not marea_data:
            st.warning("⚠️ Intenta probar con una fecha más cercana (hoy o mañana) o espera unos segundos.")
            st.stop()

        # 2. Obtener Clima
        try:
            clima_data, olas_data = obtener_datos_clima(fecha_str)
        except:
            st.error("Error obteniendo datos de viento/olas.")
            st.stop()

        # 3. Procesar
        resultados = []
        for h in range(horas[0], horas[1] + 1):
            if h >= 24: break # Seguridad
            
            # Recuperar datos
            try:
                viento = clima_data['hourly']['wind_speed_10m'][h]
                dir_v = clima_data['hourly']['wind_direction_10m'][h]
                # Olas a veces vienen nulas si no hay datos, ponemos 0
                olas = olas_data['hourly']['wave_height'][h] if olas_data['hourly']['wave_height'][h] else 0.0
                marea_hoy = marea_data[h]
            except IndexError:
                continue

            # Estado Marea
            try:
                # Comprobar límites de índice para no fallar a las 23h
                marea_next = marea_data[h+1] if h < 23 else marea_data[h]
                marea_prev = marea_data[h-1] if h > 0 else marea_data[h]
                
                if marea_hoy > marea_prev and marea_hoy > marea_next:
                    estado = "👑 PLEAMAR"
                    icono = "⛔"
                elif marea_hoy < marea_prev and marea_hoy < marea_next:
                    estado = "💀 BAJAMAR"
                    icono = "⛔"
                elif marea_next > marea_hoy:
                    estado = "⬆️ SUBIENDO"
                    icono = "✅"
                else:
                    estado = "⬇️ BAJANDO"
                    icono = "⚠️"
            except:
                estado = "-"
                icono = ""

            # Claridad
            if 45 <= dir_v <= 135: dir_txt = "Levante"
            elif 225 <= dir_v <= 315: dir_txt = "Poniente"
            else: dir_txt = "Var."
            
            if olas > 0.6 and dir_txt == "Levante": claridad = "🟤 Turbia"
            elif dir_txt == "Poniente" or olas < 0.3: claridad = "🔵 Clara"
            else: claridad = "⚪ Variable"

            resultados.append({
                "Hora": f"{h}:00",
                "Viento": f"{viento} km/h ({dir_txt})",
                "Olas": f"{olas} m",
                "Agua": claridad,
                "Marea": estado,
                "¿Ir?": icono
            })

        st.dataframe(pd.DataFrame(resultados), use_container_width=True)
        st.success("¡Datos cargados correctamente!")
