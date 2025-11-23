import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

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
ESPECIES = ["Dorada", "Lubina", "Sargo", "Mabra", "Palometón", "Anjova", "Bacoreta", "Llampuga", "Barracuda", "Palometa", "Sepia", "Pulpo", "Jurel", "Oblada", "Dentón", "Baila"]

# --- CONEXIÓN GOOGLE SHEETS (V20 - DIRECTA) ---
def conectar_sheet():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        # Leemos la configuración directamente
        if "gcp_service_account" not in st.secrets:
            st.error("❌ Error: No encuentro la cabecera [gcp_service_account] en Secrets.")
            st.stop()
            
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # Abrimos la primera hoja
        return client.open("RankingPesca").get_worksheet(0)
        
    except Exception as e:
        st.error(f"❌ Error conectando: {e}")
        st.stop()

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
    try:
        sheet = conectar_sheet()
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty and 'Peso (kg)' in df.columns:
            df['Peso (kg)'] = pd.to_numeric(df['Peso (kg)'], errors='coerce')
        return df
    except:
        return pd.DataFrame(columns=["Fecha", "Pescador", "Especie", "Peso (kg)"])

def guardar_nuevo_dato(pescador, especie, peso):
    sheet = conectar_sheet()
    fecha = datetime.now().strftime("%Y-%m-%d")
    sheet.append_row([fecha, pescador, especie, peso])

def actualizar_toda_la_hoja(df_nuevo):
    sheet = conectar_sheet()
    sheet.clear()
    datos = [df_nuevo.columns.values.tolist()] + df_nuevo.values.tolist()
    sheet.update(datos)

# --- MENÚ LATERAL ---
menu = st.sidebar.radio("Navegación", ["🔮 El Oráculo", "🏆 Ranking Capturas"])

if menu == "🔮 El Oráculo":
    st.title("🌊 Oráculo de Pesca: El Saler")
    c1, c2, c3 = st.columns(3)
    with c1: z_nom = st.selectbox("📍 Zona:", list(ZONAS.keys()))
    with c2: fecha = st.date_input("📅 Fecha:", datetime.now())
    with c3: horas = st.slider("🕒 Horas:", 0, 23, (6, 12))

    if st.button("🚀 VER PREVISIÓN"):
        lat, lon = ZONAS[z_nom]["lat"], ZONAS[z_nom]["lon"]
        fecha_str = fecha.strftime('%Y-%m-%d')
        with st.spinner('Calculando...'):
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
                    oh = olas['hourly']['wave_height'][h] if olas['hourly']['wave_height'][h] else 0.0
                    mh = tides[h]
                except: continue
                
                dt = calcular_direccion(vd)
                ag = "🟤 Turbia" if (oh>0.6 and "Levante" in dt) else ("🔵 Clara" if ("Poniente" in dt or oh<0.3) else "⚪ Variable")
                em = "🌊 Agitado" if oh>=0.4 else "💎 Planchado"
                
                prev = tides[h-1] if h>0 else mh
                sig = tides[h+1] if h < 23 else mh
                if mh>prev and mh>sig: te="🛑 PLEAMAR"; val="⛔ PARADA"
                elif mh<prev and mh<sig: te="🛑 BAJAMAR"; val="⛔ PARADA"
                elif sig>mh: te="⬆️ SUBIENDO"; val="✅ BUENA"
                else: te="⬇️ BAJANDO"; val="⚠️ REGULAR"
                tp = "🌊 CORTA (Alta)" if mh>=0.6 else "🏖️ LARGA (Baja)"
                res.append({"HORA":f"{h}:00", "VIENTO":f"{vv} {dt}", "OLAS":f"{oh}m", "AGUA":ag, "TIPO PLAYA":tp, "MAREA":te, "VAL.":val})
            st.dataframe(pd.DataFrame(res), use_container_width=True, hide_index=True)

elif menu == "🏆 Ranking Capturas":
    st.title("🏆 Liga de Pesca (Nube)")
    
    with st.expander("📝 AÑADIR NUEVA CAPTURA"):
        c1, c2 = st.columns(2)
        with c1:
            p = st.selectbox("👤 Pescador", PESCADORES)
            e = st.selectbox("🐟 Especie", ESPECIES)
        with c2:
            k = st.number_input("⚖️ Peso (kg)", 0.0, step=0.1, format="%.2f")
            if st.button("💾 Añadir"):
                if k > 0:
                    try:
                        guardar_nuevo_dato(p, e, k)
                        st.success("¡Guardado!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

    df = cargar_ranking()
    if not df.empty:
        st.markdown("### 🥇 TOP 3")
        top = df.sort_values(by="Peso (kg)", ascending=False).head(3).reset_index(drop=True)
        c1, c2, c3 = st.columns(3)
        if len(top)>0: c1.metric("🥇", f"{top.iloc[0]['Peso (kg)']}kg", top.iloc[0]['Pescador'])
        if len(top)>1: c2.metric("🥈", f"{top.iloc[1]['Peso (kg)']}kg", top.iloc[1]['Pescador'])
        if len(top)>2: c3.metric("🥉", f"{top.iloc[2]['Peso (kg)']}kg", top.iloc[2]['Pescador'])

        st.markdown("---")
        st.subheader("📝 Editar o Borrar")
        df_edit = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="editor")

        if st.button("🔄 ACTUALIZAR GOOGLE SHEETS"):
            with st.spinner("Sincronizando..."):
                actualizar_toda_la_hoja(df_edit)
            st.success("✅ Guardado"); st.rerun()
            
        st.markdown("---")
        st.bar_chart(df.groupby("Pescador")["Peso (kg)"].sum())
    else:
        st.info("La tabla está vacía. Añade la primera captura arriba.")
