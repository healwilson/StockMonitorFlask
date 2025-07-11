import requests
import re
import json
import pandas as pd
from datetime import datetime, timedelta
import numpy as np



class DataService:
    _five_days_cache = {}

    @classmethod
    def clear_stock_cache(cls, code):
        """清除指定股票的缓存"""
        if code in cls._five_days_cache:
            del cls._five_days_cache[code]

    @staticmethod
    def get_realtime_data(codes):
        """获取实时行情数据（包含涨跌幅）"""
        
        base_url = "http://qt.gtimg.cn/q="
        market_codes = []
        for c in codes:
            if not c:
                continue
            # 如果代码已带sh/sz前缀，直接使用
            if c.startswith(('sh', 'sz')):
                market_codes.append(c)
            else:
                prefix = DataService.get_market_prefix(c)
                market_codes.append(f"{prefix}{c}")

        try:
            response = requests.get(base_url + ",".join(market_codes), timeout=5)
            response.encoding = 'gbk'
            data = response.text
            stock_info = {}

            for line in data.split(';'):
                if not line:
                    continue

                parts = line.split('~')
                if len(parts) < 33:
                    continue

                # 保留完整原始代码（如 sh000001）
                raw_code = parts[0].split('=')[0].split('_')[-1]
                code = raw_code  # 不再去掉前两位
                
                # 规范化代码格式（小写）
                if code.startswith('SH'):
                    code = 'sh' + code[2:]
                elif code.startswith('SZ'):
                    code = 'sz' + code[2:]
                    
                stock_info[code] = {
                    "name": parts[1],
                    "price": float(parts[3]) if parts[3] else 0.0,
                    "changePercent": float(parts[32]) / 100 if parts[32] else 0.0  # 转换为小数
                }
            
            return stock_info
        except Exception as e:
            return {}

    @staticmethod
    def get_market_prefix(code):
        """获取股票对应的市场前缀"""
        # 深证指数支持399开头
        if code.startswith(('0', '2', '3', '399')):
            return 'sz'
        # 其他默认上证
        return 'sh'

    @staticmethod
    def get_minute_data(code):
        """获取当日分钟级数据（每分钟）基于昨收价计算涨跌幅"""
        
        try:
            # 如果代码已带sh/sz前缀，直接使用
            if code.startswith(('sh', 'sz')):
                full_code = code
            else:
                market = "sh" if code.startswith(('6', '9', '688')) else "sz"
                full_code = f"{market}{code}"
                
            url = f"https://web.ifzq.gtimg.cn/appstock/app/minute/query?code={full_code}"
            response = requests.get(url, timeout=10)
            data = response.json()

            # 获取前收盘价（昨收价）
            qt_data = data["data"][full_code].get("qt", {}).get(full_code, [0] * 5)
            close_prev = float(qt_data[4]) if len(qt_data) >= 5 else 0

            minute_data = []
            base_date = datetime.now().date()
            for item in data["data"][full_code]["data"]["data"]:
                parts = item.split()
                if len(parts) >= 3:
                    try:
                        dt_time = datetime.strptime(parts[0], "%H%M").time()
                        full_dt = datetime.combine(base_date, dt_time)
                        price = float(parts[1])
                        
                        # 使用昨收价计算涨跌幅
                        changePercent = (price - close_prev) / close_prev if close_prev != 0 else 0
                        
                        minute_data.append({
                            "datetime": full_dt,
                            "price": price,
                            "changePercent": changePercent  # 基于昨收价的涨跌幅
                        })
                    except Exception:
                        continue
            
            return minute_data
        except Exception as e:
            return []

    @staticmethod
    def get_5days_data(code):
        """获取五日分钟级数据（带缓存）"""
        
        try:
            now = datetime.now()

            # 检查缓存是否存在且有效（30秒内）
            if code in DataService._five_days_cache:
                cached_time, cached_data = DataService._five_days_cache[code]
                if (now - cached_time).total_seconds() < 30:
                    return cached_data.copy()

            # 如果代码已带sh/sz前缀，直接使用
            if code.startswith(('sh', 'sz')):
                full_code = code
            else:
                market = "sh" if code.startswith(('6', '9', '688')) else "sz"
                full_code = f"{market}{code}"
                
            url = f"https://web.ifzq.gtimg.cn/appstock/app/day/query?_var=fdays_data_{full_code}&code={full_code}"
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            json_str = re.search(r'=\s*({.*})', response.text, re.DOTALL).group(1)
            data = json.loads(json_str)

            if data.get("code") != 0:
                return []

            days_data = data["data"][full_code]["data"][-5:][::-1]  # 取最近5天并反转顺序

            # 获取最远交易日的前收盘价
            oldest_day = days_data[0]
            close_prev_oldest = float(oldest_day["prec"]) if oldest_day["prec"] else 0

            all_data = []
            for day in days_data:
                date_str = day["date"]
                try:
                    trade_date = datetime.strptime(date_str, "%Y%m%d").date()
                    for time_entry in day["data"]:
                        time_part = time_entry.split()[0]
                        dt_time = datetime.strptime(time_part, "%H%M").time()
                        full_dt = datetime.combine(trade_date, dt_time)
                        price = float(time_entry.split()[1])

                        # 计算相对于最远前收盘价的涨跌幅
                        changePercent = (price - close_prev_oldest) / close_prev_oldest if close_prev_oldest != 0 else 0

                        all_data.append({
                            "datetime": full_dt,
                            "price": price,
                            "changePercent": changePercent
                        })
                except Exception as e:
                    continue

            # 更新缓存
            DataService._five_days_cache[code] = (now, all_data.copy())
            return all_data
        except Exception as e:
            return []


class StockMonitorApp:
    def __init__(self, config):
        """初始化股票监控应用"""
        
        # 确保使用最新的配置
        self.stocks = [
            {
                "code": config.get("stock1", ""),
                "name": "",
                "price": 0.0,
                "changePercent": 0.0
            },
            {
                "code": config.get("stock2", ""),
                "name": "",
                "price": 0.0,
                "changePercent": 0.0
            }
        ]
        self.current_diff = 0.0
        self.pair_key = f"{config.get('stock1', '')}-{config.get('stock2', '')}"
        self.intraday_data = []
        self.five_day_data = []
        self.stock1_minute_data = []  # 存储股票1的当日分钟数据
        self.stock2_minute_data = []  # 存储股票2的当日分钟数据
        self.intraday_stats = {
            "current": 0.0, "current_time": "",
            "max": 0.0, "max_time": "",
            "min": 0.0, "min_time": ""
        }
        self.five_day_stats = {
            "current": 0.0,
            "current_date": "",  # 添加当前时间字段
            "max": 0.0, "max_date": "",
            "min": 0.0, "min_date": ""
        }
        
        # 初始化分时图数据
        self.stock1_chart_data = {"prices": [], "times": [], "change_percent": []}
        self.stock2_chart_data = {"prices": [], "times": [], "change_percent": []}
        
        # 定义8个主要指数的代码
        self.index_codes = [
            "sh000001", "sz399001", "sz399006", "sh000688",
            "sh000016", "sh000300", "sh000905", "sh000852"
        ]

    def update_config(self, new_config):
        """更新配置"""
        
        self.stocks[0]['code'] = new_config.get("stock1", "")
        self.stocks[1]['code'] = new_config.get("stock2", "")
        self.pair_key = f"{new_config.get('stock1', '')}-{new_config.get('stock2', '')}"
        
        # 重置数据
        self.intraday_data = []
        self.five_day_data = []
        self.stock1_minute_data = []
        self.stock2_minute_data = []
        self.intraday_stats = {
            "current": 0.0, "current_time": "",
            "max": 0.0, "max_time": "",
            "min": 0.0, "min_time": ""
        }
        self.five_day_stats = {
            "current": 0.0,
            "current_date": "",  # 添加当前时间字段
            "max": 0.0, "max_date": "",
            "min": 0.0, "min_date": ""
        }
        
        # 重置分时图数据
        self.stock1_chart_data = {"prices": [], "times": [], "change_percent": []}
        self.stock2_chart_data = {"prices": [], "times": [], "change_percent": []}
        

    def refresh_data(self):
        """刷新数据并返回前端所需格式"""
        
        try:
            self._fetch_realtime_data()
            self._fetch_minute_data()
            return self._prepare_response()
        except Exception as e:
            # 返回空数据或错误信息
            response = {
                "stock1": {"code": "", "name": "错误", "price": 0, "changePercent": 0},
                "stock2": {"code": "", "name": "错误", "price": 0, "changePercent": 0},
                "diff": {"current": 0},
                "intraday": {"data": [], "stats": {}},
                "fiveDay": {"data": [], "stats": {}},
                "stock1ChartData": {"prices": [], "times": [], "change_percent": []},
                "stock2ChartData": {"prices": [], "times": [], "change_percent": []}
            }
            
            # 添加8个指数数据的默认值
            for i in range(1, 9):
                response[f"index{i}"] = {"name": f"指数{i}", "price": 0.0, "changePercent": 0.0}
                
            return response

    def _fetch_realtime_data(self):
        """获取实时数据"""
        
        codes = [s.get('code', '') for s in self.stocks if s.get('code')]
        # 添加8个指数代码
        codes += self.index_codes
        
        if not codes:
            return

        realtime_data = DataService.get_realtime_data(codes)

        # 更新股票数据
        for stock in self.stocks:
            code = stock.get('code', '')
            if not code:
                continue

            # 检查带前缀的代码
            code_key = code
            if not code.startswith(('sh', 'sz')):
                prefix = DataService.get_market_prefix(code)
                code_key = f"{prefix}{code}"
            
            if code_key in realtime_data:
                data = realtime_data[code_key]
                stock['name'] = data.get('name', f"股票{code}")
                stock['price'] = data.get('price', 0.0)
                stock['changePercent'] = data.get('changePercent', 0.0)
            else:
                if not stock.get('name'):
                    stock['name'] = f"股票{code}"

        # 计算当前价差（当日实时价差）
        try:
            s1 = self.stocks[0].get('changePercent', 0.0)
            s2 = self.stocks[1].get('changePercent', 0.0)
            self.current_diff = s1 - s2
            self.intraday_stats['current'] = self.current_diff
            self.intraday_stats['current_time'] = datetime.now().strftime("%H:%M")
        except Exception as e:
            self.logger.error(f"Error calculating spread: {str(e)}")

    def _fetch_minute_data(self):
        """获取分钟级数据"""
        
        if not all(stock.get('code') for stock in self.stocks):
            return

        try:
            # 获取当日分钟数据
            self.stock1_minute_data = DataService.get_minute_data(self.stocks[0]['code'])
            self.stock2_minute_data = DataService.get_minute_data(self.stocks[1]['code'])

            # 处理当日数据
            self._process_intraday_data(self.stock1_minute_data, self.stock2_minute_data)

            # 获取五日数据
            stock1_5days = DataService.get_5days_data(self.stocks[0]['code'])
            stock2_5days = DataService.get_5days_data(self.stocks[1]['code'])

            # 处理五日数据
            self._process_five_day_data(stock1_5days, stock2_5days)
        except Exception as e:
            self.logger.error(f"Error fetching minute data: {str(e)}")

    def _process_intraday_data(self, data1, data2):
        """处理当日数据并计算统计"""
        self.intraday_data = []
        if not data1 or not data2:
            return

        # 创建DataFrame
        df1 = pd.DataFrame(data1)
        df2 = pd.DataFrame(data2)

        # 确保有datetime列
        if 'datetime' not in df1.columns or 'datetime' not in df2.columns:
            return

        # 按时间合并两组数据
        df1 = df1.sort_values('datetime')
        df2 = df2.sort_values('datetime')

        merged = pd.merge_asof(
            df1, df2,
            on='datetime',
            suffixes=('_1', '_2'),
            tolerance=pd.Timedelta('1min')
        ).dropna()

        # 计算价差
        merged['diff'] = merged['changePercent_1'] - merged['changePercent_2']

        # 准备分时图数据（使用合并后的数据确保一致性）
        self.stock1_chart_data = {
            "prices": merged["price_1"].tolist(),
            "times": merged["datetime"].dt.strftime("%H:%M").tolist(),
            "change_percent": merged["changePercent_1"].tolist()
        }
        
        self.stock2_chart_data = {
            "prices": merged["price_2"].tolist(),
            "times": merged["datetime"].dt.strftime("%H:%M").tolist(),
            "change_percent": merged["changePercent_2"].tolist()
        }

        # 更新数据
        for _, row in merged.iterrows():
            self.intraday_data.append({
                "time": row["datetime"].strftime("%H:%M"),
                "value": row['diff']
            })

        # 计算统计信息
        if not merged.empty:
            # 最大价差
            max_idx = merged['diff'].idxmax()
            max_row = merged.loc[max_idx]
            self.intraday_stats['max'] = max_row['diff']
            self.intraday_stats['max_time'] = max_row['datetime'].strftime("%H:%M")

            # 最小价差
            min_idx = merged['diff'].idxmin()
            min_row = merged.loc[min_idx]
            self.intraday_stats['min'] = min_row['diff']
            self.intraday_stats['min_time'] = min_row['datetime'].strftime("%H:%M")

            # 获取最新时间（最后一个数据点）
            last_row = merged.iloc[-1]
            self.intraday_stats['latest_time'] = last_row['datetime'].strftime("%H:%M")
            

    def _process_five_day_data(self, data1, data2):
        """处理五日数据并计算统计"""
        self.five_day_data = []
        if not data1 or not data2:
            return

        # 创建DataFrame
        df1 = pd.DataFrame(data1)
        df2 = pd.DataFrame(data2)

        # 确保有datetime列
        if 'datetime' not in df1.columns or 'datetime' not in df2.columns:
            return

        # 按时间合并两组数据
        df1 = df1.sort_values('datetime')
        df2 = df2.sort_values('datetime')

        merged = pd.merge_asof(
            df1, df2,
            on='datetime',
            suffixes=('_1', '_2'),
            tolerance=pd.Timedelta('5min')
        ).dropna()

        # 计算价差（基于最远前收盘价）
        merged['diff'] = merged['changePercent_1'] - merged['changePercent_2']

        # 转换为前端需要的格式 (添加完整日期时间)
        for _, row in merged.iterrows():
            self.five_day_data.append({
                "datetime": row["datetime"].strftime("%m-%d %H:%M"),
                "value": row['diff']
            })

        # 计算统计信息
        if not merged.empty:
            # 获取最新一条数据的价差和时间
            last_row = merged.iloc[-1]
            last_diff = last_row['diff']
            last_time = last_row['datetime'].strftime("%m-%d %H:%M")

            # 在整个五日数据中寻找最大价差（盘中最高点）
            max_idx = merged['diff'].idxmax()
            max_row = merged.loc[max_idx]
            max_time = max_row["datetime"].strftime("%m-%d %H:%M")

            # 在整个五日数据中寻找最小价差（盘中最低点）
            min_idx = merged['diff'].idxmin()
            min_row = merged.loc[min_idx]
            min_time = min_row["datetime"].strftime("%m-%d %H:%M")

            # 更新统计信息
            self.five_day_stats['current'] = last_diff
            self.five_day_stats['current_date'] = last_time
            self.five_day_stats['max'] = max_row['diff']
            self.five_day_stats['max_date'] = max_time
            self.five_day_stats['min'] = min_row['diff']
            self.five_day_stats['min_date'] = min_time
            

    def _prepare_response(self):
        """准备API响应数据"""
        
        # 获取8个指数的实时数据
        index_data = DataService.get_realtime_data(self.index_codes)
        
        # 构建响应数据
        response = {
            "stock1": {
                "code": self.stocks[0].get('code', ''),
                "name": self.stocks[0].get('name', ''),
                "price": self.stocks[0].get('price', 0.0),
                "changePercent": self.stocks[0].get('changePercent', 0.0)
            },
            "stock2": {
                "code": self.stocks[1].get('code', ''),
                "name": self.stocks[1].get('name', ''),
                "price": self.stocks[1].get('price', 0.0),
                "changePercent": self.stocks[1].get('changePercent', 0.0)
            },
            "diff": {
                "current": self.current_diff
            },
            "intraday": {
                "data": self.intraday_data,
                "stats": self.intraday_stats
            },
            "fiveDay": {
                "data": self.five_day_data,
                "stats": self.five_day_stats
            },
            "stock1ChartData": self.stock1_chart_data,
            "stock2ChartData": self.stock2_chart_data,
            # 添加8个指数数据
            "index1": index_data.get(self.index_codes[0], {}),
            "index2": index_data.get(self.index_codes[1], {}),
            "index3": index_data.get(self.index_codes[2], {}),
            "index4": index_data.get(self.index_codes[3], {}),
            "index5": index_data.get(self.index_codes[4], {}),
            "index6": index_data.get(self.index_codes[5], {}),
            "index7": index_data.get(self.index_codes[6], {}),
            "index8": index_data.get(self.index_codes[7], {}),
        }
        
        # 确保每个指数都有基本结构
        for i in range(1, 9):
            index_key = f"index{i}"
            if not response.get(index_key):
                response[index_key] = {"name": f"指数{i}", "price": 0.0, "changePercent": 0.0}
                
        return response

    def get_frontend_data(self):
        """获取前端所需的数据"""
        return self.refresh_data()
