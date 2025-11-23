import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import os

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Oráculo & Ranking", page_icon="🎣", layout="wide")

# --- VARIABLES ---
ZONAS = {
    "El Saler": {"lat": 39.37, "lon": -0.25},
    "Pinedo": {"lat": 39.42, "lon": -0.33},
    "Marina (Malvarrosa)": {"lat": 39.47, "lon": -0.32},
    "Alboraya": {"lat": 39.50, "lon": -0.31},
    "Faro de Cullera": {"lat": 39.18, "lon": -0.22}
}
LAT_MAREA_REF = 39.40
LON_MAREA_REF = -0.20

PESCADORES = ["Lucasthefisher", "Rodrifhising", "Megifishing", "Claudyfishing"]
ESPECIES = [
    "Dorada", "Lubina (Llobarro)", "Sargo", "Mabra (Herrera)", 
    "Palometón", "Anjova (Dorado)", "Bacoreta", "Llampuga", 
    "Barracuda (Espetón)", "Palometa (Blanca)", "Sepia", "Pulpo", 
    "Jurel", "Oblada", "Dentón", "Baila"
]
ARCHIVO_RANKING = "ranking.csv"

# --- FUNCIONES ---
def obtener_datos(lat, lon, fecha_str):
    try:
        url_clima = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=wind_speed_10m,wind_direction_10m&timezone=Europe%2FMadrid&start_date={fecha_str}&end_date={fecha_str}"
        url_olas = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&hourly=wave_height&timezone=Europe%2FMadrid&start_date={fecha_str}&end_date={fecha_str}"
        url_marea = f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT_MAREA_REF}&longitude={LON_MAREA_REF}&hourly=tide_height&timezone=Europe%2FMadrid&start_date={fecha_str}&end_date={fecha_str}"
        return requests.get(url_clima).json(), requests.get(url_olas).json(), requests.get(url_marea).json()
    except:
        return None, None, None

def calcular_direccion(grados):
    if 45 <= grados <= 135: return "Levante (E)"
    elif 225 <= grados <= 315: return "Poniente (O)"
    return "Var."

def cargar_ranking():
    if not os.path.exists(ARCHIVO_RANKING):
        return pd.DataFrame(columns=["Fecha", "Pescador", "Especie", "Peso (kg)"])
    return pd.read_csv(ARCHIVO_RANKING)

def guardar_captura(pescador, especie, peso):
    df = cargar_ranking()
    nueva_fila = pd.DataFrame([{
        "Fecha": datetime.now().strftime("%Y-%m-%d"),
        "Pescador": pescador,
        "Especie": especie,
        "Peso (kg)": peso
    }])
    df = pd.concat([df, nueva_fila], ignore_index=True)
    df.to_csv(ARCHIVO_RANKING, index=False)
    return df

# --- MENÚ LATERAL ---
menu = st.sidebar.radio("Navegación", ["🔮 El Oráculo (Previsión)", "🏆 Ranking Capturas"])

# ==============================================================================
# PANTALLA 1: EL ORÁCULO (PREVISIÓN)
# ==============================================================================
if menu == "🔮 El Oráculo (Previsión)":
    st.title("🌊 Oráculo de Pesca: El Saler")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        zona_nombre = st.selectbox("📍 Zona:", list(ZONAS.keys()))
    with col2:
        fecha = st.date_input("📅 Fecha:", datetime.now())
    with col3:
        horas = st.slider("🕒 Horas:", 0, 23, (6, 12))

    lat_zona = ZONAS[zona_nombre]["lat"]
    lon_zona = ZONAS[zona_nombre]["lon"]

    if st.button("🚀 VER PREVISIÓN"):
        fecha_str = fecha.strftime('%Y-%m-%d')
        with st.spinner('Consultando satélites...'):
            clima, olas_data, marea = obtener_datos(lat_zona, lon_zona, fecha_str)
            
            if not clima or not olas_data:
                st.error("Error de conexión.")
                st.stop()

            tides = [0]*24
            if marea and 'hourly' in marea: tides = marea['hourly']['tide_height']
            
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
                if ola_h > 0.6 and "Levante" in dir_txt: agua = "🟤 Turbia"
                elif "Poniente" in dir_txt or ola_h < 0.3: agua = "🔵 Clara"
                else: agua = "⚪ Variable"
                
                estado_mar = "🌊 Agitado" if ola_h >= 0.4 else "💎 Planchado"
                
                prev = tides[h-1] if h > 0 else marea_h
                sig = tides[h+1] if h < 23 else marea_h
                
                if marea_h > prev and marea_h > sig: tend = "🛑 PLEAMAR"; val = "⛔ PARADA"
                elif marea_h < prev and marea_h < sig: tend = "🛑 BAJAMAR"; val = "⛔ PARADA"
                elif sig > marea_h: tend = "⬆️ SUBIENDO"; val = "✅ BUENA"
                else: tend = "⬇️ BAJANDO"; val = "⚠️ REGULAR"
                
                tipo_playa = "🌊 CORTA (Alta)" if marea_h >= 0.6 else "🏖️ LARGA (Baja)"
                
                resultados.append({
                    "HORA": f"{h}:00", "VIENTO": f"{v_vel} {dir_txt}", "OLAS": f"{ola_h}m",
                    "AGUA": agua, "TIPO PLAYA": tipo_playa, "MAREA": tend, "VAL.": val
                })
            
            st.dataframe(pd.DataFrame(resultados), use_container_width=True, hide_index=True)

# ==============================================================================
# PANTALLA 2: RANKING CAPTURAS
# ==============================================================================
elif menu == "🏆 Ranking Capturas":
    st.title("🏆 Hall of Fame: Liga de Pesca")
    st.markdown("Registra tus capturas y compite por ser el rey del Mediterráneo.")
    
    # --- FORMULARIO DE REGISTRO ---
    with st.expander("📝 REGISTRAR NUEVA CAPTURA (Click aquí)", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            pescador_input = st.selectbox("👤 ¿Quién eres?", PESCADORES)
            especie_input = st.selectbox("🐟 Especie:", ESPECIES)
        with c2:
            peso_input = st.number_input("⚖️ Peso (kg):", min_value=0.0, step=0.1, format="%.2f")
            boton_guardar = st.button("💾 Guardar Captura")
        
        if boton_guardar:
            if peso_input > 0:
                guardar_captura(pescador_input, especie_input, peso_input)
                st.success(f"¡Buena pesca {pescador_input}! {especie_input} de {peso_input}kg registrada.")
            else:
                st.error("❌ El peso tiene que ser mayor que 0.")

    # --- MOSTRAR DATOS ---
    df_ranking = cargar_ranking()
    
    if not df_ranking.empty:
        # 1. EL PODIO (TOP 3 PESOS ABSOLUTOS)
        st.markdown("### 🥇 TOP 3 PIEZAS MAYORES")
        df_sorted = df_ranking.sort_values(by="Peso (kg)", ascending=False).head(3).reset_index(drop=True)
        
        col_oro, col_plata, col_bronce = st.columns(3)
        
        if len(df_sorted) > 0:
            col_oro.metric(label="🥇 ORO", value=f"{df_sorted.iloc[0]['Peso (kg)']} kg", 
                           delta=f"{df_sorted.iloc[0]['Pescador']} ({df_sorted.iloc[0]['Especie']})")
        if len(df_sorted) > 1:
            col_plata.metric(label="🥈 PLATA", value=f"{df_sorted.iloc[1]['Peso (kg)']} kg", 
                             delta=f"{df_sorted.iloc[1]['Pescador']} ({df_sorted.iloc[1]['Especie']})")
        if len(df_sorted) > 2:
            col_bronce.metric(label="🥉 BRONCE", value=f"{df_sorted.iloc[2]['Peso (kg)']} kg", 
                              delta=f"{df_sorted.iloc[2]['Pescador']} ({df_sorted.iloc[2]['Especie']})")

        # 2. TABLA COMPLETA
        st.markdown("---")
        st.markdown("### 📊 Historial Completo")
        # Colorear según pescador para que quede bonito
        st.dataframe(df_ranking.sort_values(by="Fecha", ascending=False), use_container_width=True, hide_index=True)
        
        # 3. ESTADÍSTICAS POR PESCADOR
        st.markdown("---")
        st.markdown("### 🎣 Total Kilos por Pescador")
        df_stats = df_ranking.groupby("Pescador")["Peso (kg)"].sum().sort_values(ascending=False)
        st.bar_chart(df_stats)
        
    else:
        st.info("Todavía no hay capturas registradas. ¡Sé el primero!")
