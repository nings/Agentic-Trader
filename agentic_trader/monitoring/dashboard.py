"""简单的Web仪表板服务器"""

import logging
import json
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class DashboardServer:
    """
    简单的仪表板数据服务器

    提供实时交易数据的API接口
    """

    def __init__(self, monitor, port: int = 8080):
        """
        初始化仪表板服务器

        Args:
            monitor: 交易监控器实例
            port: 端口号
        """
        self.monitor = monitor
        self.port = port

    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        获取仪表板数据

        Returns:
            仪表板数据字典
        """
        try:
            # 获取当前指标
            current_metrics = self.monitor.get_current_metrics()

            # 获取历史指标（最近1小时）
            history = self.monitor.get_metrics_history(minutes=60)

            # 准备图表数据
            chart_data = {
                'timestamps': [m.timestamp.isoformat() for m in history],
                'pnl_values': [m.daily_pnl for m in history],
                'trade_counts': [m.total_trades for m in history]
            }

            return {
                'status': 'success',
                'timestamp': datetime.now().isoformat(),
                'current_metrics': {
                    'daily_pnl': current_metrics.daily_pnl,
                    'total_trades': current_metrics.total_trades,
                    'win_rate': current_metrics.win_rate,
                    'current_positions': current_metrics.current_positions,
                    'avg_profit': current_metrics.avg_profit,
                    'avg_loss': current_metrics.avg_loss
                },
                'chart_data': chart_data,
                'system_status': {
                    'monitor_running': self.monitor.is_running,
                    'alert_rules_count': len(self.monitor.alert_rules)
                }
            }

        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def start_flask_server(self):
        """
        启动Flask Web服务器（可选）

        需要安装: pip install flask flask-cors
        """
        try:
            from flask import Flask, jsonify
            from flask_cors import CORS

            app = Flask(__name__)
            CORS(app)

            @app.route('/api/dashboard')
            def dashboard():
                return jsonify(self.get_dashboard_data())

            @app.route('/api/health')
            def health():
                return jsonify({
                    'status': 'healthy',
                    'timestamp': datetime.now().isoformat()
                })

            logger.info(f"Starting dashboard server on port {self.port}")
            app.run(host='0.0.0.0', port=self.port, debug=False)

        except ImportError:
            logger.error("Flask not installed. Install: pip install flask flask-cors")

    def export_html_dashboard(self, output_path: str = "dashboard.html"):
        """
        导出静态HTML仪表板

        Args:
            output_path: 输出文件路径
        """
        data = self.get_dashboard_data()

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Agentic Trader Dashboard</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            color: #333;
            margin-bottom: 30px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metric-label {{
            color: #666;
            font-size: 14px;
            margin-bottom: 8px;
        }}
        .metric-value {{
            font-size: 28px;
            font-weight: bold;
            color: #333;
        }}
        .metric-value.positive {{ color: #4caf50; }}
        .metric-value.negative {{ color: #f44336; }}
        .status-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }}
        .status-badge.running {{
            background: #e8f5e9;
            color: #2e7d32;
        }}
        .footer {{
            text-align: center;
            color: #999;
            margin-top: 40px;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Agentic Trader Dashboard</h1>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Daily P&L</div>
                <div class="metric-value {'positive' if data['current_metrics']['daily_pnl'] > 0 else 'negative' if data['current_metrics']['daily_pnl'] < 0 else ''}">
                    Rs.{data['current_metrics']['daily_pnl']:,.2f}
                </div>
            </div>

            <div class="metric-card">
                <div class="metric-label">Total Trades</div>
                <div class="metric-value">
                    {data['current_metrics']['total_trades']}
                </div>
            </div>

            <div class="metric-card">
                <div class="metric-label">Win Rate</div>
                <div class="metric-value">
                    {data['current_metrics']['win_rate']*100:.1f}%
                </div>
            </div>

            <div class="metric-card">
                <div class="metric-label">Current Positions</div>
                <div class="metric-value">
                    {data['current_metrics']['current_positions']}
                </div>
            </div>
        </div>

        <div class="metric-card">
            <div class="metric-label">System Status</div>
            <span class="status-badge running">
                ● Monitor Running
            </span>
            <span style="margin-left: 10px; color: #666;">
                {data['system_status']['alert_rules_count']} Alert Rules Active
            </span>
        </div>

        <div class="footer">
            Last Updated: {data['timestamp']}<br>
            Agentic Trader System v2.0
        </div>
    </div>
</body>
</html>
        """

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"Dashboard exported to {output_path}")
