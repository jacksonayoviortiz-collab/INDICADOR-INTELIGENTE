"""
data_provider.py

Clase AlphaVantageConnector para conectarse a la API de Alpha Vantage y obtener datos de Forex.
Recibe la API Key del usuario como argumento (desde la interfaz de Streamlit).
Proporciona métodos para obtener velas de un par de divisas.
Incluye manejo de errores y enlaces para obtener API Key gratuita.
"""

import requests
import pandas as pd
import logging
from typing import Optional, List
from datetime import datetime, timedelta
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AlphaVantageConnector:
    """
    Cliente para la API de Alpha Vantage.
    Documentación: https://www.alphavantage.co/documentation/
    """

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, access_token: str):
        """
        Inicializa el conector con el token de acceso del usuario.

        Args:
            access_token: API Key personal de Alpha Vantage.
        """
        self.access_token = access_token
        self.session = requests.Session()

    def _make_request(self, params: dict) -> Optional[dict]:
        """
        Realiza una petición GET a la API de Alpha Vantage y maneja errores comunes.
        """
        params['apikey'] = self.access_token
        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Alpha Vantage devuelve un JSON con 'Error Message' o 'Note' si hay problemas
            if "Error Message" in data:
                logging.error(f"Error de Alpha Vantage: {data['Error Message']}")
                return {"error": "API_ERROR", "detail": data['Error Message']}
            if "Note" in data:
                logging.warning(f"Nota de Alpha Vantage: {data['Note']}")
                # Si es un límite de tasa, lo manejamos como un error específico
                if "API call frequency" in data['Note']:
                    return {"error": "RATE_LIMIT", "detail": data['Note']}
                return {"error": "API_NOTE", "detail": data['Note']}

            return data
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                logging.error("Error 401: API Key inválida o no autorizada.")
                return {"error": "API_KEY_INVALIDA"}
            else:
                logging.error(f"Error HTTP {response.status_code}: {e}")
                return {"error": f"HTTP_{response.status_code}"}
        except requests.exceptions.ConnectionError:
            logging.error("Error de conexión: No se pudo conectar con Alpha Vantage.")
            return {"error": "CONNECTION_ERROR"}
        except requests.exceptions.Timeout:
            logging.error("Timeout: La petición tardó demasiado.")
            return {"error": "TIMEOUT"}
        except Exception as e:
            logging.error(f"Error inesperado: {e}")
            return {"error": "UNKNOWN"}

    def obtener_velas(self, from_symbol: str, to_symbol: str, interval: str = "5min") -> Optional[pd.DataFrame]:
        """
        Obtiene velas (candlesticks) para un par de divisas.

        Args:
            from_symbol: Ej. "EUR"
            to_symbol: Ej. "USD"
            interval: Resolución de las velas. Valores: "1min", "5min", "15min", "30min", "60min".

        Returns:
            DataFrame con columnas: datetime, open, high, low, close.
            Si hay error, retorna None.
        """
        params = {
            "function": "FX_INTRADAY",
            "from_symbol": from_symbol,
            "to_symbol": to_symbol,
            "interval": interval,
            "outputsize": "compact",  # Las últimas 100 velas
            "datatype": "json"
        }

        data = self._make_request(params)

        if data is None or "Time Series FX" not in data:
            if data and data.get("error") == "API_KEY_INVALIDA":
                logging.error("API Key inválida al obtener velas.")
            return None

        # La clave tiene un formato como "Time Series FX (5min)"
        time_series_key = f"Time Series FX ({interval})"
        series = data.get(time_series_key, {})

        if not series:
            logging.error(f"No se encontraron datos para el intervalo {interval}.")
            return None

        records = []
        for timestamp, values in series.items():
            records.append({
                "datetime": timestamp,
                "open": float(values["1. open"]),
                "high": float(values["2. high"]),
                "low": float(values["3. low"]),
                "close": float(values["4. close"])
            })

        df = pd.DataFrame(records)
        df["datetime"] = pd.to_datetime(df["datetime"])
        df.set_index("datetime", inplace=True)
        df.sort_index(inplace=True)
        return df

    def obtener_par_ejemplo(self) -> tuple:
        """Devuelve un par de ejemplo para probar la conexión."""
        return ("EUR", "USD")

    @staticmethod
    def obtener_instrucciones_api_key() -> str:
        """
        Devuelve un texto con instrucciones y enlace para obtener una API Key gratuita de Alpha Vantage.
        """
        return (
            "🔑 **Para usar este indicador, necesitas una API Key gratuita de Alpha Vantage.**\n\n"
            "1. **Regístrate** en este enlace (es inmediato):\n"
            "   👉 [https://www.alphavantage.co/support/#api-key](https://www.alphavantage.co/support/#api-key)\n"
            "2. Llena el formulario con tu nombre, email y sitio web.\n"
            "3. **Recibirás tu API Key por email** en menos de 1 minuto (revisa spam).\n"
            "4. Pega el token en el campo de abajo y listo.\n\n"
            "*(La API Key es gratuita y te permite 5 llamadas por minuto, perfecto para empezar.)*"
        )
