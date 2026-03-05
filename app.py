"""
app.py - Interfaz principal del indicador FUERZA-IQ
Conector OANDA, visualización de datos y placeholders para análisis.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time
import logging

# Importamos nuestro conector
from data_provider import OandaConnector

# Configuración de la página
st.set_page_config(
    page_title="FUERZA-IQ",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Título principal
st.markdown("<h1 style='text-align: center; color:#00FF88;'>💪 INDICADOR FUERZA-IQ</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align: center; color:#AAAAAA;'>Análisis de fuerza y volumen con OANDA</h4>", unsafe_allow_html=True)
st.markdown("---")

# Inicializar estado de sesión
if 'conectado' not in st.session_state:
    st.session_state.conectado = False
if 'connector' not in st.session_state:
    st.session_state.connector = None
if 'activos' not in st.session_state:
    st.session_state.activos = []
if 'activo_seleccionado' not in st.session_state:
    st.session_state.activo_seleccionado = None
if 'datos_velas' not in st.session_state:
    st.session_state.datos_velas = None
if 'analizar' not in st.session_state:
    st.session_state.analizar = False

# --- Barra lateral de configuración ---
with st.sidebar:
    st.markdown("### 🔐 Conexión OANDA")
    if not st.session_state.conectado:
        api_key = st.text_input("API Key", type="password", placeholder="Ingresa tu token")
        environment = st.selectbox("Entorno", ["practice", "real"], index=0)
        if st.button("🔌 Conectar", use_container_width=True):
            if api_key:
                with st.spinner("Conectando a OANDA..."):
                    connector = OandaConnector(access_token=api_key, environment=environment)
                    # Probamos la conexión obteniendo velas de EUR/USD
                    df_test = connector.obtener_velas("EUR_USD", count=5)
                    if df_test is not None:
                        st.session_state.conectado = True
                        st.session_state.connector = connector
                        # Lista de activos predefinida (puedes ampliarla)
                        st.session_state.activos = [
                            "EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USDCAD",
                            "NZD_USD", "USDCHF", "EUR_GBP", "EUR_JPY", "GBP_JPY"
                        ]
                        st.success("✅ Conectado correctamente")
                        st.rerun()
                    else:
                        st.error("❌ Error de conexión. Verifica tu API Key.")
                        st.info(OandaConnector.obtener_instrucciones_api_key())
            else:
                st.warning("Ingresa una API Key")
    else:
        st.success("✅ Conectado")
        st.metric("Estado", "Conectado a OANDA")
        if st.button("🚪 Desconectar", use_container_width=True):
            st.session_state.conectado = False
            st.session_state.connector = None
            st.rerun()

    if st.session_state.conectado and st.session_state.activos:
        st.markdown("---")
        st.markdown("### 📊 Activo a analizar")
        activo = st.selectbox(
            "Selecciona un par",
            st.session_state.activos,
            index=0,
            format_func=lambda x: x.replace("_", "/")
        )
        st.session_state.activo_seleccionado = activo

        st.markdown("---")
        st.markdown("### ⚙️ Análisis")
        if st.button("▶️ Escanear ahora", use_container_width=True):
            st.session_state.analizar = True
        else:
            st.session_state.analizar = False

# --- Cuerpo principal ---
if not st.session_state.conectado:
    # Mostrar instrucciones para obtener API Key
    st.info(OandaConnector.obtener_instrucciones_api_key())
    # Mostrar un placeholder visual
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="background:#1E242C; border-radius:20px; padding:30px; text-align:center;">
            <i class="fas fa-plug" style="font-size:50px; color:#00FF88;"></i>
            <h3 style="color:#00FF88;">Conéctate a OANDA para comenzar</h3>
        </div>
        """, unsafe_allow_html=True)
else:
    # Mostrar información del activo seleccionado
    if st.session_state.activo_seleccionado:
        st.subheader(f"📈 Activo: {st.session_state.activo_seleccionado.replace('_', '/')}")

        # Si se ha solicitado análisis, obtenemos datos y mostramos gráfico
        if st.session_state.analizar:
            with st.spinner("Obteniendo datos de OANDA..."):
                df = st.session_state.connector.obtener_velas(
                    st.session_state.activo_seleccionado,
                    granularity="M5",
                    count=100
                )
                if df is not None:
                    st.session_state.datos_velas = df
                else:
                    st.error("No se pudieron obtener datos. Intenta de nuevo.")

        # Mostrar gráfico si hay datos
        if st.session_state.datos_velas is not None:
            df = st.session_state.datos_velas

            # Crear gráfico de velas
            fig = go.Figure(data=[go.Candlestick(
                x=df.index,
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                increasing_line_color='#00FF88',
                decreasing_line_color='#FF4646'
            )])
            fig.update_layout(
                title=f"{st.session_state.activo_seleccionado.replace('_', '/')} - Últimas {len(df)} velas (5m)",
                height=500,
                paper_bgcolor="#0F1217",
                plot_bgcolor="#0F1217",
                font_color="#E0E0E0",
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=False),
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)

            # Mostrar estadísticas básicas
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Precio actual", f"{df['close'].iloc[-1]:.5f}")
            with col2:
                st.metric("Volumen (última vela)", f"{df['volume'].iloc[-1]:,.0f}")
            with col3:
                st.metric("Máximo (10 velas)", f"{df['high'].iloc[-10:].max():.5f}")
            with col4:
                st.metric("Mínimo (10 velas)", f"{df['low'].iloc[-10:].min():.5f}")

            # Placeholder para análisis de fuerza
            st.markdown("---")
            st.subheader("🔍 Análisis de fuerza y volumen")
            st.info("Aquí aparecerán las señales generadas por la IA en futuras versiones.")

            # Simulación de notificación proactiva
            st.success("🔔 Alerta: El activo muestra acumulación de volumen. Podría generarse una señal pronto.")
        else:
            st.info("Presiona 'Escanear ahora' para cargar los datos del activo.")
    else:
        st.info("Selecciona un activo en la barra lateral.")
