"""
data_provider.py

Clase OandaConnector para conectarse a la API de OANDA y obtener datos de mercado.
Recibe la API Key del usuario como argumento (desde la interfaz de Streamlit).
Proporciona métodos para obtener velas históricas de un instrumento.
Incluye manejo de errores y enlaces para obtener API Key gratuita.
"""

import requests
import pandas as pd
import logging
from typing import Optional, List

# Configurar logging básico (se puede sobreescribir desde la app)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class OandaConnector:
    """
    Cliente para la API REST de OANDA (v3).
    Documentación oficial: http://developer.oanda.com/rest-live-v3/introduction/
    """

    # URLs base para cuentas de práctica y real
    BASE_URLS = {
        "practice": "https://api-fxpractice.oanda.com/v3/",
        "real": "https://api-fxtrade.oanda.com/v3/"
    }

    def __init__(self, access_token: str, environment: str = "practice"):
        """
        Inicializa el conector con el token de acceso del usuario.
        
        Args:
            access_token: API Key personal de OANDA (obtenida en el sitio web).
            environment: "practice" para cuenta demo, "real" para cuenta real.
        """
        self.access_token = access_token
        self.environment = environment
        self.base_url = self.BASE_URLS.get(environment, self.BASE_URLS["practice"])
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        })

    def _make_request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """
        Realiza una petición GET a la API de OANDA y maneja errores comunes.
        """
        url = self.base_url + endpoint
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()  # Lanza excepción para códigos 4xx/5xx
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                logging.error("Error 401: API Key inválida o no autorizada.")
                return {"error": "API_KEY_INVALIDA"}
            elif response.status_code == 404:
                logging.error(f"Error 404: Recurso no encontrado. Endpoint: {endpoint}")
                return {"error": "NOT_FOUND"}
            else:
                logging.error(f"Error HTTP {response.status_code}: {e}")
                return {"error": f"HTTP_{response.status_code}"}
        except requests.exceptions.ConnectionError:
            logging.error("Error de conexión: No se pudo conectar con OANDA.")
            return {"error": "CONNECTION_ERROR"}
        except requests.exceptions.Timeout:
            logging.error("Timeout: La petición tardó demasiado.")
            return {"error": "TIMEOUT"}
        except Exception as e:
            logging.error(f"Error inesperado: {e}")
            return {"error": "UNKNOWN"}

    def obtener_instrumentos(self) -> List[str]:
        """
        Obtiene la lista de instrumentos (pares) disponibles para la cuenta.
        Útil para mostrar al usuario y permitir selección.
        """
        endpoint = "accounts"
        data = self._make_request(endpoint)
        if data and "accounts" in data:
            # Primero necesitamos el accountID. Normalmente se obtiene de /accounts
            account_id = data["accounts"][0]["id"]
            endpoint = f"accounts/{account_id}/instruments"
            data_instr = self._make_request(endpoint)
            if data_instr and "instruments" in data_instr:
                return [inst["name"] for inst in data_instr["instruments"]]
        return []

    def obtener_velas(self, instrument: str, granularity: str = "M5", count: int = 200) -> Optional[pd.DataFrame]:
        """
        Obtiene velas (candlesticks) para un instrumento dado.

        Args:
            instrument: Ej. "EUR_USD", "GBP_JPY", etc.
            granularity: Resolución de las velas. Valores comunes: "M1", "M5", "M15", "H1", etc.
            count: Número de velas a obtener (máx 5000).

        Returns:
            DataFrame con columnas: time, volume, open, high, low, close.
            Si hay error, retorna None.
        """
        endpoint = f"instruments/{instrument}/candles"
        params = {
            "price": "M",          # Precio mid (promedio bid/ask)
            "granularity": granularity,
            "count": count
        }
        data = self._make_request(endpoint, params)

        if data is None or "candles" not in data:
            if data and data.get("error") == "API_KEY_INVALIDA":
                # Podemos propagar el error para que la interfaz lo muestre
                logging.error("API Key inválida al obtener velas.")
            return None

        candles = data["candles"]
        records = []
        for c in candles:
            # OANDA devuelve velas completas o incompletas. Filtramos solo las completas si queremos.
            # Para análisis en tiempo real, podemos usar la última aunque sea incompleta.
            # Aquí incluimos todas.
            records.append({
                "time": c["time"],
                "volume": c["volume"],
                "open": float(c["mid"]["o"]),
                "high": float(c["mid"]["h"]),
                "low": float(c["mid"]["l"]),
                "close": float(c["mid"]["c"])
            })

        df = pd.DataFrame(records)
        df["time"] = pd.to_datetime(df["time"])
        df.set_index("time", inplace=True)
        df.sort_index(inplace=True)
        return df

    @staticmethod
    def obtener_instrucciones_api_key() -> str:
        """
        Devuelve un texto con instrucciones y enlace para obtener una API Key gratuita de OANDA.
        Útil para mostrar en la interfaz cuando la clave es inválida.
        """
        return (
            "🔑 **Para usar este indicador, necesitas una API Key de OANDA (gratuita para cuenta demo).**\n\n"
            "1. **Regístrate** en OANDA (si no tienes cuenta):\n"
            "   👉 [https://www.oanda.com/demo-account/](https://www.oanda.com/demo-account/)\n"
            "2. Una vez registrado, **inicia sesión** en tu cuenta demo.\n"
            "3. Ve a **'Administrar API'** (o 'Manage API Access') en el panel de control.\n"
            "4. **Genera una nueva API Key** (token). Copia el token completo.\n"
            "5. Pega el token en el campo de abajo y selecciona el entorno **'practice'**.\n\n"
            "🔗 **Enlace directo para generar API Key** (requiere haber iniciado sesión):\n"
            "   👉 [https://www.oanda.com/account/tpa/personal_token](https://www.oanda.com/account/tpa/personal_token)\n\n"
            "*(La API Key es gratuita y solo necesitas una cuenta demo para probar el indicador.)*"
        )
