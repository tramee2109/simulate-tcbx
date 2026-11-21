import time
import json
import redis
import requests
import math
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

class The20FuturesPrivate:
    """
    Class for interacting with The20 exchange Futures API.
    Adapts structure from Aster Futures Private V3 to The20 simulation API.
    Uses username/password authentication to obtain a bearer token.
    """
    def __init__(self, symbol, quote='USDT', api_key='', secret_key='', passphrase='', session_key='', strategy_name='', testnet=False):
        self.symbol = symbol
        self.quote = quote
        self.base = symbol
        self.symbol_ex = f'{symbol}{quote}'.upper()
        self.symbol_redis = f'{symbol}_{quote}'.upper()
        self.username = api_key
        self.password = secret_key
        self.session_key = session_key
        self.strategy_name = strategy_name
        self.base_url = "https://simulation.the20.sg"


        self.api_base_path = "/fapi/v1/simulation/future"
        self.r = r
        self.token = None
        self.refresh_token = None
        self.qty_scale = 0x22
        self.price_scale = 0
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        
        self._login()
        
        scale_redis = r.get(f'{self.symbol_redis}_the20_futures_scale')
        if scale_redis is not None:
            scale = json.loads(scale_redis)
            self.price_scale, self.qty_scale = int(scale["priceScale"]), int(scale["qtyScale"])
        else:
            self.price_scale, self.qty_scale = self.get_scale()
            scale = json.dumps({'priceScale': self.price_scale, 'qtyScale': self.qty_scale})
            r.set(f'{self.symbol_redis}_the20_futures_scale', scale)

    def _login(self):
        try:
            url = f"{self.base_url}/api/v1/auth/login/trader"
            payload = {
                "username": self.username,
                "password": self.password
            }
            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            self.token = data.get('token') or data.get('access_token')
            self.refresh_token = data.get('refresh_token')
            if not self.token:
                raise Exception("Failed to obtain authentication token")
        except Exception as e:
            raise Exception(f"Login failed: {str(e)}")

    def _refresh_token_call(self):
        try:
            if not self.refresh_token:
                return self._login()
            url = f"{self.base_url}/api/v1/auth/refresh"
            payload = {"refresh_token": self.refresh_token}
            response = self.session.post(url, json=payload, timeout=30)
            if response.status_code != 200:
                return self._login()
            data = response.json()
            self.token = data.get('token') or data.get('access_token')
            self.refresh_token = data.get('refresh_token')
        except Exception as e:
            return self._login()

    def _request(self, method, path, params=None, body=None, signed=True):
        headers = {}
        if params is None: params = {}
        if body is None: body = {}
        
        if signed and self.token:
            headers.update({"Authorization": f"Bearer {self.token}"})
        
        url = f"{self.base_url}{self.api_base_path}{path}"
        print('url: ',url)
        if self.session_key or self.strategy_name or signed:
            target = body if method in ["POST", "PUT", "PATCH"] else params
            # Only send session_key for GET requests to avoid API timeout/deadlocks on state-modifying endpoints
            if self.session_key and method == "GET" and "session_key" not in target:
                target["session_key"] = self.session_key
            if self.strategy_name and "strategyName" not in target:
                target["strategyName"] = self.strategy_name

        try:
            response = self.session.request(
                method,
                url,
                headers=headers,
                timeout=30,
                params=params,
                json=body if method in ["POST", "PUT", "PATCH"] else None
            )
            
            if response.status_code == 401 and signed:
                self._refresh_token_call()
                if self.token:
                    headers.update({"Authorization": f"Bearer {self.token}"})
                    response = self.session.request(
                        method,
                        url,
                        headers=headers,
                        timeout=30,
                        params=params,
                        json=body if method in ["POST", "PUT", "PATCH"] else None
                    )
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"API Request failed: {method} {path} - {e}")
            try:
                return response.json()
            except:
                return {"error": str(e)}
    def get_scale(self):
        endpoint = '/exchangeInfo'
        result = self._request('GET', endpoint, signed=False)
        if 'symbols' in result:
            for symbol_info in result['symbols']:
                if symbol_info['symbol'] == self.symbol_ex:
                    price_filter = next((f for f in symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER'), None)
                    lot_filter = next((f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE'), None)
                    
                    price_scale = 2
                    qty_scale = 3
                    
                    if price_filter:
                        price_scale = int(-math.log10(float(price_filter["tickSize"])))
                    if lot_filter:
                        qty_scale = int(-math.log10(float(lot_filter["stepSize"])))
                        
                    return price_scale, qty_scale
        return 2, 5

    def get_orderbook(self, symbol: str = None, limit: int = 100) -> Dict[str, Any]:
        endpoint = '/depth'
        params = {'symbol': symbol or self.symbol_ex, 'limit': limit}
        return self._request('GET', endpoint, params, signed=False)

    def get_ticker(self, symbol: str = None) -> Dict[str, Any]:
        endpoint = '/ticker/24hr'
        params = {'symbol': symbol or self.symbol_ex}
        return self._request('GET', endpoint, params, signed=False)

    def get_server_time(self) -> Dict[str, Any]:
        endpoint = '/time'
        return self._request('GET', endpoint, signed=False)

    def get_exchange_info(self) -> Dict[str, Any]:
        endpoint = '/exchangeInfo'
        return self._request('GET', endpoint, signed=False)

    def get_funding_rate(self, symbol: str = None, start_time: int = None, end_time: int = None, limit: int = 100) -> Dict[str, Any]:
        endpoint = '/fundingRate'
        params = {'symbol': symbol or self.symbol_ex, 'limit': limit}
        if start_time: params['startTime'] = start_time
        if end_time: params['endTime'] = end_time
        return self._request('GET', endpoint, params, signed=False)

    def get_mark_price(self, symbol: str = None) -> Dict[str, Any]:
        endpoint = '/premiumIndex'
        params = {'symbol': symbol or self.symbol_ex}
        return self._request('GET', endpoint, params, signed=False)

    def get_candles(self, interval: str = "1h", limit: int = 200, start_time: int = None, end_time: int = None, symbol: str = None) -> Dict[str, Any]:
        endpoint = '/klines'
        params = {
            'symbol': symbol or self.symbol_ex,
            'interval': interval,
            'limit': limit
        }
        if start_time: params['startTime'] = start_time
        if end_time: params['endTime'] = end_time
        
        result = self._request('GET', endpoint, params, signed=False)
        if isinstance(result, list):
            candles = []
            for item in result:
                candles.append([
                    int(item[0]), float(item[1]), float(item[2]), float(item[3]),
                    float(item[4]), float(item[5]), int(item[6]), float(item[7])
                ])
            return {"ts": int(time.time() * 1000), "candle": candles}
        return result

    def get_account_assets(self, coin: str = "") -> Dict[str, Any]:
        endpoint = '/account'
        result = self._request('GET', endpoint, signed=True)
        if 'assets' in result:
            for asset in result['assets']:
                if asset['asset'] == coin or not coin:
                    return {
                        'asset': asset.get("asset", ""),
                        'available': float(asset.get("availableBalance", 0)),
                        'locked': float(asset.get("positionInitialMargin", 0)),
                        'total': float(asset.get("walletBalance", 0)) + float(asset.get("unrealizedProfit", 0)),
                        'unrealizedProfit': float(asset.get("unrealizedProfit", 0))
                    }
        return {}

    def get_account_balance(self) -> Dict[str, Any]:
        endpoint = '/balance'
        response = self._request('GET', endpoint, signed=True)
        print('response: ',response)
        return response

    def place_order(self, order_side: str, quantity: float, order_type: str, 
                   price: float = None, position_side: str = "BOTH", time_in_force: str = "GTC", 
                   reduce_only: bool = False, stop_price: float = None,
                   working_type: str = "MARK_PRICE", order_link_id: str = None, **kwargs) -> Dict[str, Any]:
        endpoint = '/order'
        params = {
            'symbol': self.symbol_ex,
            'side': order_side.upper(),
            'type': order_type.upper(),
            'quantity': round(float(quantity), self.qty_scale),
            'positionSide': position_side,
            'timeInForce': time_in_force
        }
        if price: params['price'] = round(float(price), self.price_scale)
        if stop_price: params['stopPrice'] = round(float(stop_price), self.price_scale)
        if order_link_id: params['newClientOrderId'] = order_link_id
        if reduce_only: params['reduceOnly'] = 'true'
        if working_type: params['workingType'] = working_type
        params.update(kwargs)
        
        return self._request('POST', endpoint, body=params, signed=True)

    def cancel_order(self, order_id: str = None, client_order_id: str = None) -> Dict[str, Any]:
        endpoint = '/order'
        params = {'symbol': self.symbol_ex}
        if order_id: params['orderId'] = order_id
        if client_order_id: params['origClientOrderId'] = client_order_id
        return self._request('DELETE', endpoint, params=params, signed=True)

    def cancel_orders(self, symbol: str = None, strategy_name: str = None) -> Dict[str, Any]:
        endpoint = '/allOpenOrders'
        params = {'symbol': symbol or self.symbol_ex}
        strat = strategy_name if strategy_name is not None else self.strategy_name
        if strat:
            params['strategyName'] = strat
        return self._request('DELETE', endpoint, params=params, signed=True)

    def cancel_all_orders(self, symbol: str = None, strategy_name: str = None) -> Dict[str, Any]:
        return self.cancel_orders(symbol, strategy_name)

    def get_open_orders(self, symbol: str = None) -> Dict[str, Any]:
        endpoint = '/openOrders'
        params = {'symbol': symbol or self.symbol_ex}
        return self._request('GET', endpoint, params, signed=True)

    def get_all_orders(self, symbol: str = None, order_id: str = None, start_time: int = None, end_time: int = None, limit: int = 500) -> Dict[str, Any]:
        endpoint = '/allOrders'
        params = {'symbol': symbol or self.symbol_ex, 'limit': limit}
        if order_id: params['orderId'] = order_id
        if start_time: params['startTime'] = start_time
        if end_time: params['endTime'] = end_time
        return self._request('GET', endpoint, params, signed=True)

    def get_position(self, symbol: str = None) -> Dict[str, Any]:
        endpoint = '/positionRisk'
        params = {'symbol': symbol or self.symbol_ex}
        return self._request('GET', endpoint, params, signed=True)

    def get_position_risk(self, symbol: str = None) -> Dict[str, Any]:
        return self.get_position(symbol)

    def get_all_positions(self) -> Dict[str, Any]:
        endpoint = '/positionRisk'
        return self._request('GET', endpoint, signed=True)

    def set_leverage(self, leverage: int, symbol: str = None) -> Dict[str, Any]:
        endpoint = '/leverage'
        params = {'symbol': symbol or self.symbol_ex, 'leverage': leverage}
        return self._request('POST', endpoint, body=params, signed=True)

    def set_margin_type(self, margin_type: str, symbol: str = None) -> Dict[str, Any]:
        endpoint = '/marginType'
        params = {'symbol': symbol or self.symbol_ex, 'marginType': margin_type.upper()}
        return self._request('POST', endpoint, body=params, signed=True)

    def modify_position_margin(self, amount: float, margin_type: int, symbol: str = None, position_side: str = "BOTH") -> Dict[str, Any]:
        endpoint = '/positionMargin'
        params = {
            'symbol': symbol or self.symbol_ex,
            'amount': amount,
            'type': margin_type,
            'positionSide': position_side
        }
        return self._request('POST', endpoint, body=params, signed=True)

    def change_position_mode(self, dual_side_position: bool) -> Dict[str, Any]:
        endpoint = '/positionSide/dual'
        params = {'dualSidePosition': str(dual_side_position).lower()}
        return self._request('POST', endpoint, body=params, signed=True)

    def get_position_mode(self) -> Dict[str, Any]:
        endpoint = '/positionSide/dual'
        return self._request('GET', endpoint, signed=True)

    def get_user_trades(self, symbol: str = None, start_time: int = None, end_time: int = None, from_id: str = None, limit: int = 500) -> List[Dict[str, Any]]:
        endpoint = '/userTrades'
        params = {'symbol': symbol or self.symbol_ex, 'limit': limit}
        if start_time: params['startTime'] = start_time
        if end_time: params['endTime'] = end_time
        if from_id: params['fromId'] = from_id
        return self._request('GET', endpoint, params, signed=True)

    def get_income_history(self, symbol: str = None, income_type: str = None, start_time: int = None, end_time: int = None, limit: int = 100) -> List[Dict[str, Any]]:
        endpoint = '/income'
        params = {'limit': limit}
        if symbol: params['symbol'] = symbol
        if income_type: params['incomeType'] = income_type
        if start_time: params['startTime'] = start_time
        if end_time: params['endTime'] = end_time
        return self._request('GET', endpoint, params, signed=True)

    def get_leverage_bracket(self, symbol: str = None) -> List[Dict[str, Any]]:
        endpoint = '/leverageBracket'
        params = {'symbol': symbol or self.symbol_ex}
        return self._request('GET', endpoint, params, signed=True)

    def get_adl_quantile(self, symbol: str = None) -> List[Dict[str, Any]]:
        endpoint = '/adlQuantile'
        params = {'symbol': symbol or self.symbol_ex}
        return self._request('GET', endpoint, params, signed=True)

    def get_commission_rate(self, symbol: str = None) -> Dict[str, Any]:
        endpoint = '/commissionRate'
        params = {'symbol': symbol or self.symbol_ex}
        return self._request('GET', endpoint, params, signed=True)
    
    def get_order_details(self, order_id: str = None, client_order_id: str = None) -> Dict[str, Any]:
        """
        Retrieves details of a specific order.
        """
        endpoint = '/order'
        params = {'symbol': self.symbol_ex}
        if order_id: params['orderId'] = order_id
        if client_order_id: params['origClientOrderId'] = client_order_id
        
        return self._request('GET', endpoint, params=params, signed=True)
