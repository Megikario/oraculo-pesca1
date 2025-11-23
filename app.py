import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Oráculo & Ranking", page_icon="🎣", layout="wide")

# ==============================================================================
# 🎨 SECCIÓN DE ESTILO (CSS) - AQUÍ OCURRE LA MAGIA VISUAL
# ==============================================================================
def configurar_estilo():
    # URL de la imagen de fondo (puedes cambiarla por otra que te guste)
    imagen_fondo = "https://images.unsplash.com/photo-1533601017-dc61895e03c0?q=80&w=2070&auto=format&fit=crop"
    
    st.markdown(f"""
    <style>
    /* 1. PONER IMAGEN DE FONDO */
    .stApp {{
        background-image: url("{imagen_fondo}");
        background-attachment: fixed;
        background-size: cover;
    }}

    /* 2. BARRA LATERAL (SIDEBAR) SEMI-TRANSPARENTE */
    [data-testid="stSidebar"] {{
        background-color: rgba(0, 20, 40, 0.85); /* Azul muy oscuro transparente */
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }}
    
    /* 3. COLORES DE TEXTO PARA QUE SE LEAN BIEN SOBRE EL FONDO */
    h1, h2, h3, h4, p, label {{
        color: #FFFFFF !important;
        text-shadow: 2px 2px 4px #000000; /* Sombra negra para leer mejor */
    }}
    
    /* 4. BOTONES PERSONALIZADOS */
    div.stButton > button {{
        background-color: #00A8E8;
        color: white;
        border-radius: 10px;
        border: none;
        padding: 10px 24px;
        font-weight: bold;
        transition: 0.3s;
    }}
    div.stButton > button:hover {{
        background-color: #0077B6;
        border: 2px solid white;
        transform: scale(1.05);
    }}

    /* 5. CAJAS DE DATOS (METRICAS) */
    [data-testid="stMetricValue"] {{
        color: #00E5FF !important; /* Color Cyan para los números */
    }}
    
    /* 6. TABLAS */
    .stDataFrame {{
        background-color: rgba(0, 0, 0, 0.6); /* Fondo negro transparente para tablas */
        border-radius: 10px;
        padding: 10px;
    }}
    </style>
    """, unsafe_allow_html=True)

# Aplicamos el estilo nada más empezar
configurar_estilo()

# ==============================================================================
# LÓGICA DEL PROGRAMA (VARIABLES Y FUNCIONES)
# ==============================================================================

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
ESPECIES = ["Dorada", "Lubina", "Sargo", "Mabra", "Palometón", "Anjova", "Bacoreta", "Llampuga", "Barracuda", "Palometa", "Sepia", "Pulpo", "Jurel", "Oblada", "Dentón", "Baila"]

def conectar_sheet():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        if "gcp_service_account" not in st.secrets:
            st.error("❌ Falta Secrets."); st.stop()
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("RankingPesca").get_worksheet(0)
    except Exception as e: st.error(f"Error: {e}"); st.stop()

def icono_tiempo(code):
    if code == 0: return "☀️ Despejado"
    if code in [1, 2, 3]: return "⛅ Nuboso"
    if code in [45, 48]: return "🌫️ Niebla"
    if code in [51, 53, 55, 61, 63, 65]: return "🌧️ Lluvia"
    if code >= 80: return "⛈️ Tormenta"
    return "🌤️ Variable"

def obtener_datos(lat, lon, fecha_str):
    try:
        url_clima = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=wind_speed_10m,wind_direction_10m,temperature_2m,weather_code&timezone=Europe%2FMadrid&start_date={fecha_str}&end_date={fecha_str}"
        url_olas = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&hourly=wave_height,sea_surface_temperature&timezone=Europe%2FMadrid&start_date={fecha_str}&end_date={fecha_str}"
        url_marea = f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT_MAREA_REF}&longitude={LON_MAREA_REF}&hourly=tide_height&timezone=Europe%2FMadrid&start_date={fecha_str}&end_date={fecha_str}"
        return requests.get(url_clima).json(), requests.get(url_olas).json(), requests.get(url_marea).json()
    except: return None, None, None

def calcular_direccion(grados):
    if 45 <= grados <= 135: return "Levante (E)"
    elif 225 <= grados <= 315: return "Poniente (O)"
    return "Var."

def cargar_ranking():
    try:
        sheet = conectar_sheet()
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if df.empty: return pd.DataFrame(columns=["Fecha", "Pescador", "Especie", "Peso (kg)"])
        df.columns = df.columns.str.strip()
        if "Peso (kg)" not in df.columns: return pd.DataFrame(columns=["Fecha", "Pescador", "Especie", "Peso (kg)"])
        df['Peso (kg)'] = pd.to_numeric(df['Peso (kg)'], errors='coerce').fillna(0)
        return df
    except: return pd.DataFrame(columns=["Fecha", "Pescador", "Especie", "Peso (kg)"])

def guardar_nuevo_dato(pescador, especie, peso):
    sheet = conectar_sheet()
    fecha = datetime.now().strftime("%Y-%m-%d")
    sheet.append_row([fecha, pescador, especie, peso])

def actualizar_toda_la_hoja(df_nuevo):
    sheet = conectar_sheet()
    sheet.clear()
    headers = df_nuevo.columns.values.tolist()
    datos = [headers] + df_nuevo.values.tolist()
    sheet.update(datos)

# ==============================================================================
# INTERFAZ GRÁFICA
# ==============================================================================

menu = st.sidebar.radio("Navegación", ["🔮 El Oráculo", "🏆 Ranking Capturas"])

if menu == "🔮 El Oráculo":
    st.markdown("<h1 style='text-align: center;'>🌊 Oráculo de Pesca: El Saler</h1>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Usamos contenedores para agrupar visualmente
    with st.container():
        c1, c2, c3 = st.columns(3)
        with c1: z_nom = st.selectbox("📍 Selecciona Zona", list(ZONAS.keys()))
        with c2: fecha = st.date_input("📅 Fecha", datetime.now())
        with c3: horas = st.slider("🕒 Horario", 0, 23, (6, 12))

    if st.button("🚀 VER PREVISIÓN"):
        lat, lon = ZONAS[z_nom]["lat"], ZONAS[z_nom]["lon"]
        fecha_str = fecha.strftime('%Y-%m-%d')
        with st.spinner('📡 Conectando con boyas meteorológicas...'):
            clima, olas, marea = obtener_datos(lat, lon, fecha_str)
            
            if not clima: st.error("Error conexión"); st.stop()
            
            tides = [0]*24
            if marea and 'hourly' in marea: tides = marea['hourly']['tide_height']
            
            res = []
            for h in range(horas[0], horas[1]+1):
                if h>=24: break
                try:
                    vv = clima['hourly']['wind_speed_10m'][h]
                    vd = clima['hourly']['wind_direction_10m'][h]
                    dt = calcular_direccion(vd)
                    temp_aire = clima['hourly']['temperature_2m'][h]
                    cod_cielo = clima['hourly']['weather_code'][h]
                    txt_cielo = icono_tiempo(cod_cielo)
                    oh = olas['hourly']['wave_height'][h] if olas['hourly']['wave_height'][h] else 0.0
                    temp_agua = olas['hourly']['sea_surface_temperature'][h] if olas['hourly']['sea_surface_temperature'][h] else "--"
                    mh = tides[h]
                except: continue
                
                ag = "🟤 Turbia" if (oh>0.6 and "Levante" in dt) else ("🔵 Clara" if ("Poniente" in dt or oh<0.3) else "⚪ Variable")
                prev = tides[h-1] if h>0 else mh
                sig = tides[h+1] if h < 23 else mh
                if mh>prev and mh>sig: te="🛑 PLEAMAR"
                elif mh<prev and mh<sig: te="🛑 BAJAMAR"
                elif sig>mh: te="⬆️ SUBIENDO"
                else: te="⬇️ BAJANDO"
                tp = "🌊 CORTA (Alta)" if mh>=0.6 else "🏖️ LARGA (Baja)"
                
                info_clima = f"{txt_cielo} {temp_aire}°C  |  💧Agua: {temp_agua}°C"

                res.append({
                    "HORA": f"{h}:00", 
                    "CLIMA": info_clima,
                    "VIENTO": f"{vv} {dt}", 
                    "OLAS": f"{oh}m", 
                    "AGUA": ag, 
                    "TIPO PLAYA": tp, 
                    "MAREA": te
                })
            
            st.dataframe(pd.DataFrame(res), use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.caption(f"📍 Mapa de zona: {z_nom}")
            st.map(pd.DataFrame({'lat': [lat], 'lon': [lon]}), zoom=12)

elif menu == "🏆 Ranking Capturas":
    st.markdown("<h1 style='text-align: center;'>🏆 Liga de Pesca</h1>", unsafe_allow_html=True)
    
    with st.expander("📝 REGISTRAR NUEVA CAPTURA"):
        c1, c2 = st.columns(2)
        with c1:
            p = st.selectbox("👤 Pescador", PESCADORES)
            e = st.selectbox("🐟 Especie", ESPECIES)
        with c2:
            k = st.number_input("⚖️ Peso (kg)", 0.0, step=0.1, format="%.2f")
            if st.button("💾 GUARDAR EN NUBE"):
                if k > 0:
                    try: guardar_nuevo_dato(p, e, k); st.success("¡Guardado!"); st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

    df = cargar_ranking()
    if not df.empty and "Peso (kg)" in df.columns:
        st.markdown("### 🥇 PODIO ACTUAL")
        try:
            top = df.sort_values(by="Peso (kg)", ascending=False).head(3).reset_index(drop=True)
            c1, c2, c3 = st.columns(3)
            # Usamos metricas personalizadas
            if len(top)>0: c1.metric("🥇 ORO", f"{top.iloc[0]['Peso (kg)']}kg", top.iloc[0]['Pescador'])
            if len(top)>1: c2.metric("🥈 PLATA", f"{top.iloc[1]['Peso (kg)']}kg", top.iloc[1]['Pescador'])
            if len(top)>2: c3.metric("🥉 BRONCE", f"{top.iloc[2]['Peso (kg)']}kg", top.iloc[2]['Pescador'])
        except: pass

        st.markdown("---")
        st.subheader("📝 Tabla Editable")
        df_edit = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="editor")
        if st.button("🔄 SINCRONIZAR CAMBIOS"):
            with st.spinner("Guardando..."): actualizar_toda_la_hoja(df_edit)
            st.success("✅ Actualizado"); st.rerun()
        
        st.markdown("---")
        try: st.bar_chart(df.groupby("Pescador")["Peso (kg)"].sum())
        except: pass
    else: st.info("Tabla vacía. ¡Añade la primera captura!")
