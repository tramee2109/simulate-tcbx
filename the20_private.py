import time
import json
import redis
import requests
from typing import Optional, Dict, Any
from utils import calculate_gap_hours, get_candle_data_info, convert_order_status
from urllib.parse import urlencode



import urllib.request
import json
from datetime import datetime
from urllib.parse import urlencode



base_url = "https://simulation.the20.sg"
r = redis.Redis(host='localhost', port=6379, decode_responses=True)


class The20Private:
    """
    Class for interacting with The20 exchange using the private API.
    Uses token-based authentication via login/trader endpoint.
    """
    def __init__(self, symbol, quote='USDT', api_key='', secret_key='', passphrase = '', session_key='', strategy_name=''):
        self.symbol = symbol
        self.quote = quote
        self.base = symbol
        self.symbol_ex = f'{symbol}_{self.quote}'.upper()
        self.symbol_redis = f'{symbol}_{quote}'.upper()
        self.username = api_key
        self.password = secret_key
        self.session_key = session_key
        self.strategy_name = strategy_name
        self.strategy_name = strategy_name
        self.base_url = base_url.rstrip("/")
        self.api_base_path = "/api/v1/simulation"
        self.api_path = "/api/v1/simulation"
        self.r = r
        self.token = None
        self.qty_scale = 0
        self.price_scale = 0
        self.session = requests.Session()
        
        self._login()
        
        scale_redis = r.get(f'{self.symbol_redis}_the20_scale')
        if scale_redis is not None:
            scale = json.loads(scale_redis)
            self.price_scale, self.qty_scale = int(scale["priceScale"]), int(scale["qtyScale"])
        else:
            self.price_scale, self.qty_scale = self.get_scale()
            scale = json.dumps({'priceScale': self.price_scale, 'qtyScale': self.qty_scale})
            r.set(f'{self.symbol_redis}_the20_scale', scale)
    
    
    def _login(self):
        """
        Login to the trader API and obtain authentication token.
        """
        try:
            url = f"{self.base_url}/api/v1/auth/login/trader"
            payload = {
                "username": self.username,
                "password": self.password
            }
            response = self.session.post(url, json=payload, timeout=5)
            response.raise_for_status()
            data = response.json()
            self.token = data.get('token')
            if not self.token:
                raise Exception("Failed to obtain authentication token")
        except Exception as e:
            raise Exception(f"Login failed: {str(e)}")
    
    
    def _request(self, method, path, params=None, body=None):
        """
        Execute an API request with token authentication.
        
        Args:
            method (str): HTTP method (GET, POST, DELETE, etc.)
            path (str): API endpoint path (will be prefixed with api_base_path)
            params (dict): Query parameters
            body (dict): Request body
            
        Returns:
            JSON response from server
        """
        headers = {}
        
        if params is None:
            params = {}
        if body is None:
            body = {}
        
        if len(body) > 0:
            headers.update({'content-type': 'application/json'})
            body = json.dumps(body)
        
        if self.token:
            headers.update({'Authorization': f'Bearer {self.token}'})
        
        full_path = f"{self.api_base_path}{path}"
        url = f"{self.base_url}{full_path}"
        response = self.session.request(
            method,
            url,
            headers=headers,
            timeout=20,
            params=params,
            data=body if isinstance(body, str) else (json.dumps(body) if body else None)
        )
        
        try:
            response_json = response.json()
        except Exception as exc:
            if response.status_code != 200:
                response.raise_for_status()
            raise RuntimeError(response.text) from exc
        
        # if response.status_code != 200:
        #     raise Exception(f"API Error: {response_json.get('error', response.text)}")
        
        return response_json
    
    
    def _api_get_candles(self, session_key: str, symbol: str, interval: str = '1m') -> Optional[Dict[str, Any]]:
        """
        Retrieve candle data from simulation-api.
        
        Args:
            session_key: Session key for the user
            symbol: Trading symbol (e.g., BTC_USDT)
            interval: Candle interval (1m, 5m, 15m, 30m, 1h, 4h, etc.)
        
        Returns:
            Candle data from API or None if not found
        """
        try:
            url = f"{self.base_url}{self.api_path}/klines"
            params = {
                "session_key": session_key,
                "symbol": symbol,
                "interval": interval
            }
            response = self.session.get(url, params=params, timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error retrieving candles: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error retrieving candles: {e}")
        return None
    
    
    def _api_get_ticker(self, session_key: str, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve ticker data from simulation-api.
        
        Args:
            session_key: Session key for the user
            symbol: Trading symbol (e.g., BTC_USDT)
        
        Returns:
            Ticker data from API or None if not found
        """
        try:
            url = f"{self.base_url}{self.api_path}/ticker/24hr"
            params = {
                "session_key": session_key,
                "symbol": symbol
            }
            response = self.session.get(url, params=params, timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error retrieving ticker: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error retrieving ticker: {e}")
        return None
    
    
    def _api_get_orderbook(self, session_key: str, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve orderbook data from simulation-api.
        
        Args:
            session_key: Session key for the user
            symbol: Trading symbol (e.g., BTC_USDT)
        
        Returns:
            Orderbook data from API or None if not found
        """
        try:
            url = f"{self.base_url}{self.api_path}/depth"
            params = {
                "session_key": session_key,
                "symbol": symbol
            }
            response = self.session.get(url, params=params, timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error retrieving orderbook: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error retrieving orderbook: {e}")
        return None
    
    
    def _api_get_account_asset(self, session_key: str, user_id: int = None) -> Optional[Dict[str, Any]]:
        """
        Retrieve account asset data from simulation-api.
        
        Args:
            session_key: Session key for authentication
            user_id: User ID (optional, extracted from context if not provided)
        
        Returns:
            Account balance data with current_tokens_value and current_token_balance
        """
        try:
            url = f"{self.base_url}{self.api_path}/account/asset"
            params = {
                "session_key": session_key
            }
            response = self.session.get(url, params=params, timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error retrieving account asset: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error retrieving account asset: {e}")
        return None
    
    
    def validate_session_key(self, session_key: str) -> bool:
        """
        Validate session key by attempting to retrieve account asset.
        
        Args:
            session_key: Session key to validate
        
        Returns:
            True if session key is valid, False otherwise
        """
        try:
            data = self._api_get_account_asset(session_key)
            return data is not None
        except Exception as e:
            print(f"Error validating session key: {e}")
        return False
    
    
    def get_candles(self, base="", quote="", interval='1m', limit=200, start_time=0):
        """Retrieves candlestick (K-line) data from The20 API and formats it."""
        candles_list = {
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "1h": "1h",
            "4h": "4h",
            "6h": "6h",
            "12h": "12h",
            "1d": "1d",
            "3d": "3d",
            "1w": "1w",
            "1M": "1M", 
        }
         
        symbol = f'{base}_{quote}'.upper()
        if base == "":
            symbol = self.symbol_ex
        
        params_map = {
            "symbol": symbol,
            "interval": candles_list.get(interval, "1h"),
            "limit": limit,
        }
        if start_time:
            params_map["startTime"] = start_time
        
        if self.session_key:
            params_map["session_key"] = self.session_key
            
        result = self._request('GET', '/klines', params=params_map)
        if isinstance(result, list):
            candles = []
            for item in result:
                candles.append([
                    int(item[0]),
                    float(item[1]),
                    float(item[2]),
                    float(item[3]),
                    float(item[4]),
                    float(item[5]),
                    int(item[0]),
                    float(item[7])
                ])
            return {"ts": int(time.time() * 1000), "candle": candles}
        return result
    
    
    def get_ticker(self, base="", quote=""):
        """
        Retrieves the ticker information for a given symbol.
        """
        symbol = f'{base}_{quote}'.upper()
        if base == "":
            symbol = self.symbol_ex
        
        params = {'symbol': symbol}
        if self.session_key:
            params['session_key'] = self.session_key
            
        result = self._request('GET', '/ticker/24hr', params=params)
        if not isinstance(result, dict):
            return None  

        ticker_data = result
        formatted_ticker = {
            "ts": ticker_data.get("time"),
            "ts-sv": int(time.time() * 1000),
            "last": ticker_data.get("lastPr"),
            "lastPr": ticker_data.get("lastPr"),
            "baseVolume": ticker_data.get("baseVolume"),
            "quoteVolume": ticker_data.get("quoteVolume"),
            "bidPr": ticker_data.get("bidPr"),
            "bestBid": ticker_data.get("bidPr"),
            "askPr": ticker_data.get("askPr"),
            "bestAsk": ticker_data.get("askPr"),
            "bidSz": ticker_data.get("bidSz"),
            "askSz": ticker_data.get("askSz")
        }
        return formatted_ticker
    
    
    def get_orderbook(self, base: str = "", quote: str = "USDT", depth: int = 50):
        """
        Retrieves the orderbook (depth) data from The20 API.
        
        Args:
            base (str): The base currency symbol. If empty, uses self.symbol.
            quote (str): The quote currency symbol. Defaults to 'USDT'.
            depth (int): The depth of the orderbook to retrieve. Defaults to 50.
            
        Returns:
            dict: A dictionary containing:
                - ts: Client timestamp
                - ts-sv: Server timestamp
                - bids: Dictionary of bid prices to quantities
                - asks: Dictionary of ask prices to quantities
        """
        symbol = f'{base}_{quote}'.upper() if base else self.symbol_ex
        symbol_key = f"{(base or self.symbol).upper()}_{(quote or self.quote).upper()}"
        cache_key = f"{symbol_key}_the20_orderbook"
        
        try:
            cached_orderbook = r.get(cache_key)
            if cached_orderbook:
                return json.loads(cached_orderbook)
        except Exception:
            pass
        
        params = {
            'symbol': symbol,
            'limit': depth
        }
        if self.session_key:
            params['session_key'] = self.session_key
        
        response = self._request('GET', '/depth', params=params)
        if isinstance(response, dict):
            orderbook = {
                "ts": response.get('ts',0),
                "ts-sv": response.get('ts',0),
                "bids": dict(
                    sorted(
                        response.get('bids', {}).items(),
                        key=lambda x: float(x[0]),
                        reverse=True
                    )
                ),
                "asks": dict(
                    sorted(
                        response.get('asks', {}).items(),
                        key=lambda x: float(x[0])
                    )
                ),
            }
            try:
                r.set(cache_key, json.dumps(orderbook, separators=(",", ":")), ex=2)
            except Exception:
                pass
            return orderbook
        
        return response
    
    def get_scale(self, base="", quote=""):
        """
        Retrieves the price and quantity scales for the trading pair from The20 API.
        Proxies through backend to fetch from Binance and return in Binance format.
        """
        symbol = f'{base}_{quote}'.upper()
        if base == "":
            symbol = self.symbol_ex
        symbol_for_api = symbol.replace("_", "").replace("-", "")
        try:
            params = {'symbol': symbol_for_api}
            if self.session_key:
                params['session_key'] = self.session_key
            result = self._request('GET', '/exchangeInfo', params=params)
            if isinstance(result, dict):
                if 'symbols' in result and len(result['symbols']) > 0:
                    symbol_info = result['symbols'][0]
                    qty_scale = 8
                    price_scale = 8
                    if 'filters' in symbol_info:

                        for filter_item in symbol_info['filters']:
                            if filter_item.get('filterType') == 'LOT_SIZE':
                                step_size = filter_item.get('stepSize', '0.00000001')
                                if '.' in step_size:
                                    decimal_part = step_size.split('.')[1].rstrip('0')
                                    qty_scale = len(decimal_part) if decimal_part else 0
                            if filter_item.get('filterType') == 'PRICE_FILTER':
                                tick_size = filter_item.get('tickSize', '0.00000001')
                                if '.' in tick_size:
                                    decimal_part = tick_size.split('.')[1].rstrip('0')
                                    price_scale = len(decimal_part) if decimal_part else 0
                    
                    return price_scale, qty_scale
                else:
                    print(f"Warning: Response has no symbols or empty symbols list. Response: {result}")
            else:
                print(f"Warning: Expected dict response, got {type(result)}. Response: {result}")

            return 8, 8
        except Exception as e:
            print(f"Warning: Failed to get scale from exchangeInfo: {e}, using defaults")
            import traceback
            traceback.print_exc()
            return 8, 8
    
    
    def get_account_balance(self, account_type=None):
        """
        Retrieves all account assets (tokens) from The20 API.
        Returns a dictionary with all assets containing amount/available/locked/total balances.
        """
        cache_key = f'the20_{self.username}_balance'
        cached_data = r.get(cache_key)
        if cached_data is not None:
            return {'data': json.loads(cached_data)}
        
        if not self.session_key:
            print("Error: session_key is required for get_account_balance")
            return {'data': {}}
        
        params = {}
        if account_type is not None:
            params.update({'accountType': account_type})
        
        if self.session_key:
            params['session_key'] = self.session_key

        result = self._request('GET', '/account/balance', params=params)
        
        if isinstance(result, dict) and 'data' in result:
            try:
                tokens_data = result['data']
                if isinstance(tokens_data, str):
                    tokens_data = json.loads(tokens_data)
                
                account_balance = {}
                if isinstance(tokens_data, dict):
                    for asset_key, asset_value in tokens_data.items():
                        if asset_key.upper() == 'TOTAL':
                            continue
                        if isinstance(asset_value, dict):
                            data = {
                                "asset": asset_key,
                                "available": float(asset_value.get("amount", 0)),
                                "locked": float(asset_value.get("locked", 0)),
                                "total": float(asset_value.get("total", asset_value.get("amount", 0)))
                            }
                            if data["total"] > 0:
                                account_balance[data["asset"]] = data
                
                r.set(cache_key, json.dumps(account_balance), ex=5)
                return {'data': account_balance}
            except Exception as e:
                print(f"Error parsing account balance: {e}")
                return {'data': {}}
        
        r.set(cache_key, json.dumps({}), ex=5)
        return {'data': {}}
    
    
    def get_account_assets(self, coin, account_type=None):
        """
        Retrieves the account assets for a given coin.
        Returns a single asset with available, locked, and total balance.
        """
        cache_key = f'the20_{self.username}_assets'
        cached_data = r.get(cache_key)
        if cached_data is not None:
            try:
                cached_dict = json.loads(cached_data)
                if coin in cached_dict:
                    return {'data': cached_dict[coin]}
            except Exception:
                pass
        
        if not self.session_key:
            print("Error: session_key is required for get_account_assets")
            return {'data': {}}
        
        params = {
            'session_key': self.session_key,
            'coin': coin
        }
        if account_type is not None:
            params['accountType'] = account_type

        result = self._request('GET', '/account/asset', params=params)
        if isinstance(result, dict) and 'data' in result:
            try:
                asset_value = result['data']
                if isinstance(asset_value, str):
                    asset_value = json.loads(asset_value)
                
                if isinstance(asset_value, dict):
                    data = {
                        "asset": coin,
                        "available": float(asset_value.get("amount", 0)),
                        "locked": float(asset_value.get("locked", 0)),
                        "total": float(asset_value.get("total", asset_value.get("amount", 0)))
                    }
                    
                    try:
                        all_assets = r.get(cache_key)
                        if all_assets:
                            assets_dict = json.loads(all_assets)
                        else:
                            assets_dict = {}
                        assets_dict[coin] = data
                        r.set(cache_key, json.dumps(assets_dict), ex=5)
                    except Exception:
                        pass
                    
                    return {'data': data}
            except Exception as e:
                print(f"Error parsing account assets: {e}")
                return {'data': {}}
        
        r.set(cache_key, json.dumps({}), ex=5)
        return {'data': {}}

    def get_user_asset(self, account_type=None):
        """
        Retrieves the user's assets and calculates the base inventory, quote inventory, 
        and USDT inventory based on the assets' availability and locks.
        """
        base_inventory, quote_inventory, quote_usdt_inventory = 0, 0, 0
        params = {}
        if account_type is not None:
            params.update({'accountType': account_type})
        
        if self.session_key:
            params['session_key'] = self.session_key

        result = self._request('GET', '/account/balance', params=params)
        if isinstance(result, dict) and 'data' in result:
            reps = result['data']
            for asset, data in reps.items():
                if not isinstance(data, dict):
                    continue

                available = float(data.get("available", data.get("amount", 0)))
                locked = float(data.get("locked", 0))
                total = available + locked

                if total <= 0:
                    continue

                if asset == self.quote:
                    quote_inventory += total
                elif asset == "USDT":
                    quote_usdt_inventory += total
                elif asset == self.base:
                    base_inventory += total

        return base_inventory, quote_inventory, quote_usdt_inventory

    
    def get_price(self):
        """Get Price of a symbol"""
        symbol = f'{self.base}_{self.quote}'.upper()
        if self.base == "":
            symbol = self.symbol_ex
        
        params = {'symbol': symbol}
        if self.session_key:
            params['session_key'] = self.session_key
        return self._request('GET', '/ticker/price', params=params)
    
    def place_order(
        self,
        order_side,
        quantity,
        order_type,
        price=None,
        strategy_name=None,
        force='GTC'
    ):
        symbol = self.symbol_ex if self.base == "" else f'{self.base}_{self.quote}'.upper()

        if float(quantity) <= 0:
            raise ValueError("Quantity must be positive")

        params = {
            "symbol": symbol,
            "side": order_side.upper(),
            "type": order_type.upper(),
            "quantity": float(quantity),
            "timeInForce": force
        }

        if params["type"] == "LIMIT":
            if price is None:
                raise ValueError("LIMIT order requires price")
            params["price"] = float(price)

        if params["type"] == "MARKET":
            params.pop("timeInForce", None)

        strat = strategy_name or self.strategy_name
        if strat:
            params["strategyName"] = strat

        # session_key is not used by POST /order and causes simulation API to timeout
        # if self.session_key:
        #     params["session_key"] = self.session_key

        reps = self._request('POST', '/order', body=params)
        oid = reps.get("orderId") or reps.get("orderID")

        if not oid:
            return False

        return {"data": reps, "code": 0}
    
    # def cancel_order(self, order_id=None, strategy_name=None):
    #     """
    #     Cancel an active order.

    #     Args:
    #         order_id (str, optional): Order's id

    #     Returns:
    #         Json object with information on deleted order
    #     """
    #     if order_id is None:
    #         raise ValueError('cancel_order endpoint requires order_id')

    #     symbol = f'{self.base}_{self.quote}'.upper()
    #     if self.base == "":
    #         symbol = self.symbol_ex

    #     from urllib.parse import urlencode
        
    #     params = {
    #         'symbol': symbol,
    #         'orderId': order_id
    #     }
        
    #     # session_key and strategyName are not used by CancelOrder endpoint
    #     # and can cause issues if included
            
    #     path = f'/order?{urlencode(params)}'
    #     result =  self._request('DELETE', path)
    #     print('result: ',result)
    #     return result

    def cancel_order(self, order_id=None, strategy_name=None):
        """
        Cancel an active order.

        Args:
            order_id (str, optional): Order's id

        Returns:
            Json object with information on deleted order
        """
        if order_id is None:
            raise ValueError('cancel_order endpoint requires order_id')

        symbol = f'{self.base}_{self.quote}'.upper()
        if self.base == "":
            symbol = self.symbol_ex

        path = '/order'
        params = {
            'symbol': symbol,
            'orderId': order_id
        }
        
        # session_key is not used by DELETE /order and causes simulation API to timeout
        # if self.session_key:
        #     params['session_key'] = self.session_key
        
        strat = strategy_name if strategy_name is not None else self.strategy_name
        if strat:
            params['strategyName'] = strat
        
        try:
            self._request('DELETE', path, params=params)
            return {"code": "0"}
        except Exception as e:
            return {"code": "1", "error": str(e)}


    def cancel_all_orders(self, symbol=None, strategy_name=None):
        """Cancels all open orders for a symbol on The20 exchange."""
        """Cancels all open orders for a symbol on The20 exchange."""
        symbol = f'{self.base}_{self.quote}'.upper()
        if self.base == "":
            symbol = self.symbol_ex
            
        if symbol is None:
            raise ValueError('cancel_orders endpoint requires symbol')

        body = {'symbol': symbol}
        # session_key is not used by DELETE /openOrders and causes simulation API to timeout
        # if self.session_key:
        #     body['session_key'] = self.session_key
        
        strat = strategy_name if strategy_name is not None else self.strategy_name
        if strat:
            body['strategyName'] = strat
        
        strat = strategy_name if strategy_name is not None else self.strategy_name
        if strat:
            body['strategyName'] = strat
        return self._request('DELETE', '/openOrders', body=body)
        
    def get_order_details(self, order_id=None, strategy_name=None):
        """Retrieves details of a specific order on The20 exchange."""
        if order_id is None:
            raise ValueError('get_order_details endpoint requires order_id')

        symbol = f'{self.base}_{self.quote}'.upper()
        if self.base == "":
            symbol = self.symbol_ex

        params = {
            'symbol': symbol,
            'orderId': int(order_id)
        }
        
        if self.session_key:
            params['session_key'] = self.session_key
        
        strat = strategy_name if strategy_name is not None else self.strategy_name
        if strat:
            params['strategyName'] = strat
        
        strat = strategy_name if strategy_name is not None else self.strategy_name
        if strat:
            params['strategyName'] = strat
        
        result = self._request('GET', '/order', params=params)
        
        if not isinstance(result, dict) or "orderId" not in result:
            return {
                "code": "1",
                "error": "ORDER_NOT_FOUND",
                "data": result
            }

        order_details = {
            "orderId": result["orderId"],
            "clientOrderId": result.get("clientOrderId"),
            "quantity": float(result.get("origQty", 0.0)),
            "filledQuantity": float(result.get("executedQty", 0.0)),
            "price": float(result.get("price", 0.0)),
            "status": result.get("status"),
            "side": result.get("side"),
            "type": result.get("type"),
            "createTime": result.get("time"),
            "updateTime": result.get("updateTime")
        }

        return {
            "code": "0",
            "data": order_details
        }

    def get_open_orders(self, symbol=None, limit=None, strategy_name=None):
        """Retrieves all open orders on The20 exchange."""
        if symbol is None:
            symbol = f'{self.base}_{self.quote}'.upper()
        if symbol == "":
            symbol = self.symbol_ex

        params = {'symbol': symbol}
        if limit is not None:
            params['limit'] = limit
        if self.session_key:
            params['session_key'] = self.session_key
        
        strat = strategy_name if strategy_name is not None else self.strategy_name
        if strat:
            params['strategyName'] = strat
        
        strat = strategy_name if strategy_name is not None else self.strategy_name
        if strat:
            params['strategyName'] = strat
        
        result = self._request('GET', '/openOrders', params=params)
        if isinstance(result, list):
            for item in result:
                item.update({
                    "fillQuantity": item.get("executedQty", 0),
                    "quantity": item.get("origQty", 0),
                    "fillPrice": item.get("price", 0),
                    "status": item.get("status", ""),
                    "orderType": item.get("type", ""),
                    "createTime": item.get("time", 0),
                    "updateTime": item.get("updateTime", 0),
                    "orderId": item.get("orderId")
                })

        return {"data": result if isinstance(result, list) else []}
    
    
    def get_all_orders(self, symbol=None, limit=None, strategy_name=None):
        """Retrieves all orders (open and closed) on The20 exchange."""
        if symbol is None:
            symbol = f'{self.base}_{self.quote}'.upper()
        if symbol == "":
            symbol = self.symbol_ex

        params = {'symbol': symbol}
        if limit is not None:
            params['limit'] = limit
        if self.session_key:
            params['session_key'] = self.session_key
        
        strat = strategy_name if strategy_name is not None else self.strategy_name
        if strat:
            params['strategyName'] = strat
        
        strat = strategy_name if strategy_name is not None else self.strategy_name
        if strat:
            params['strategyName'] = strat
        
        result = self._request('GET', '/allOrders', params=params)
        if isinstance(result, list):
            for item in result:
                item.update({
                    "fillQuantity": item.get("executedQty", 0),
                    "quantity": item.get("origQty", 0),
                    "fillPrice": item.get("price", 0),
                    "status": item.get("status", ""),
                    "orderType": item.get("type", ""),
                    "createTime": item.get("time", 0),
                    "updateTime": item.get("updateTime", 0),
                    "orderId": item.get("orderId")
                })

        return {"data": result if isinstance(result, list) else []}


    def snap_shot_account(self, coin_list=None):
        """
        Generates a snapshot of the account balances for a given list of coins.
        """
        if coin_list is None:
            coin_list = ['USDT', 'BTC', 'BNB']
        
        total_balance = []
        balance_asset_temp = {}
        telegram_snap_shot = {
            'type': 'TELEGRAM_TOTAL'
        }

        balances_spot = {
            'type': 'SPOT'
        }
        spot_assets_list = self.get_account_balance() if not self.session_key else {'data': {}}
        for keys, value in spot_assets_list['data'].items():
            balances_spot_keys = f'{keys}'
            total = value['total']
            balances_spot[balances_spot_keys] = total
            if balances_spot_keys not in balance_asset_temp:
                balance_asset_temp[balances_spot_keys] = 0
            balance_asset_temp[balances_spot_keys] += total
        total_balance.append(balances_spot)

        for asset_snap_shot in coin_list:
            if asset_snap_shot not in balance_asset_temp:
                telegram_snap_shot[asset_snap_shot] = 0
            else:
                telegram_snap_shot[asset_snap_shot] = balance_asset_temp[asset_snap_shot]
        total_balance.append(telegram_snap_shot)

        return total_balance
    
    

    def get_candles_from_api(self, symbol='', quote='', interval='1m'):
        """
        Retrieve candle data from simulation-api server.
        
        Args:
            symbol: Base symbol (uses self.symbol if empty)
            quote: Quote symbol (uses self.quote if empty)
            interval: Candle interval (1m, 5m, 15m, 30m, 1h, 4h, etc.)
        
        Returns:
            Candle data or None if error or no session_key
        """
        if not self.session_key:
            return None
        
        sym = symbol if symbol else self.symbol
        q = quote if quote else self.quote
        api_symbol = f'{sym}_{q}'.upper()
        return self._api_get_candles(self.session_key, api_symbol, interval)
    
    def get_ticker_from_api(self, symbol='', quote=''):
        """
        Retrieve ticker data from simulation-api server.
        
        Args:
            symbol: Base symbol (uses self.symbol if empty)
            quote: Quote symbol (uses self.quote if empty)
        
        Returns:
            Ticker data or None if error or no session_key
        """
        if not self.session_key:
            return None
        
        sym = symbol if symbol else self.symbol
        q = quote if quote else self.quote
        api_symbol = f'{sym}_{q}'.upper()
        return self._api_get_ticker(self.session_key, api_symbol)
    
    def get_orderbook_from_api(self, symbol='', quote=''):
        """
        Retrieve orderbook data from simulation-api server.
        
        Args:
            symbol: Base symbol (uses self.symbol if empty)
            quote: Quote symbol (uses self.quote if empty)
        
        Returns:
            Orderbook data or None if error or no session_key
        """
        if not self.session_key:
            return None
        
        sym = symbol if symbol else self.symbol
        q = quote if quote else self.quote
        api_symbol = f'{sym}_{q}'.upper()
        return self._api_get_orderbook(self.session_key, api_symbol)
    
    def get_account_asset_from_api(self):
        """
        Retrieve account asset data from simulation-api server.
        
        Returns:
            Account asset data with current_tokens_value and current_token_balance
        """
        if not self.session_key:
            return None
        return self._api_get_account_asset(self.session_key)

    def get_volume_by_interval(self, symbol_input, quote_input, interval, start_time):
        """
        Retrieves the volume of a given symbol and quote within a specified interval and time range.
        """
        redis_klines = get_candle_data_info(symbol_redis=f"{symbol_input}_{quote_input}", exchange_name="the20", interval=interval, r=r)
        tick_number = calculate_gap_hours(start_time, int(time.time() * 1000))
        if redis_klines is not None:
            return {'data': redis_klines['candle'][-tick_number:]}
        klines = self.get_candles(base=symbol_input, 
                                    quote=quote_input, 
                                    interval=interval, 
                                    start_time=start_time) if not self.session_key else {'data': []}
        return {'data': klines['candle']}
