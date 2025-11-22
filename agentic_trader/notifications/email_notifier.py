"""邮件通知器"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailNotifier:
    """
    邮件通知器

    发送交易告警和报告到邮箱
    """

    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        sender_email: str,
        sender_password: str,
        recipient_emails: List[str],
        use_tls: bool = True
    ):
        """
        初始化邮件通知器

        Args:
            smtp_server: SMTP服务器地址
            smtp_port: SMTP端口
            sender_email: 发件人邮箱
            sender_password: 发件人密码/应用密码
            recipient_emails: 收件人邮箱列表
            use_tls: 是否使用TLS
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.recipient_emails = recipient_emails
        self.use_tls = use_tls

        logger.info(f"EmailNotifier initialized for {len(recipient_emails)} recipients")

    def send_email(
        self,
        subject: str,
        body: str,
        is_html: bool = False
    ) -> Dict[str, Any]:
        """
        发送邮件

        Args:
            subject: 主题
            body: 正文
            is_html: 是否为HTML格式

        Returns:
            发送结果
        """
        try:
            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = ', '.join(self.recipient_emails)

            # 添加正文
            mime_type = 'html' if is_html else 'plain'
            msg.attach(MIMEText(body, mime_type))

            # 连接SMTP服务器
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)

            server.login(self.sender_email, self.sender_password)

            # 发送邮件
            server.sendmail(
                self.sender_email,
                self.recipient_emails,
                msg.as_string()
            )

            server.quit()

            logger.info(f"Email sent successfully: {subject}")

            return {
                "success": True,
                "subject": subject,
                "recipients": self.recipient_emails
            }

        except Exception as e:
            logger.error(f"Failed to send email: {e}")

            return {
                "success": False,
                "error": str(e)
            }

    def send_alert(
        self,
        severity: str,
        message: str,
        timestamp: Optional[datetime] = None
    ):
        """
        发送告警邮件

        Args:
            severity: 严重程度
            message: 告警消息
            timestamp: 时间戳
        """
        timestamp = timestamp or datetime.now()

        # 根据严重程度设置主题前缀
        prefix_map = {
            "critical": "🚨 CRITICAL",
            "warning": "⚠️ WARNING",
            "info": "ℹ️ INFO",
            "success": "✅ SUCCESS"
        }

        prefix = prefix_map.get(severity.lower(), "📢 ALERT")
        subject = f"{prefix} - Trading Alert"

        # HTML格式邮件
        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif;">
    <h2 style="color: {'#d32f2f' if severity == 'critical' else '#f57c00' if severity == 'warning' else '#1976d2'};">
        {prefix}
    </h2>

    <div style="background-color: #f5f5f5; padding: 20px; border-radius: 5px; margin: 20px 0;">
        <p style="font-size: 16px; line-height: 1.6;">
            {message.replace('\n', '<br>')}
        </p>
    </div>

    <p style="color: #666; font-size: 12px;">
        <strong>Time:</strong> {timestamp.strftime('%Y-%m-%d %H:%M:%S')}
    </p>

    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">

    <p style="color: #999; font-size: 11px;">
        This is an automated alert from Agentic Trader System.
    </p>
</body>
</html>
        """

        return self.send_email(subject, html_body, is_html=True)

    def send_daily_report(
        self,
        metrics: Dict[str, Any],
        trade_details: Optional[List[Dict]] = None
    ):
        """
        发送每日报告

        Args:
            metrics: 指标字典
            trade_details: 交易详情列表
        """
        daily_pnl = metrics.get('daily_pnl', 0)
        total_trades = metrics.get('total_trades', 0)
        win_rate = metrics.get('win_rate', 0) * 100

        # 生成交易表格
        trades_table = ""
        if trade_details:
            trades_table = "<h3>Trade Details:</h3><table style='border-collapse: collapse; width: 100%;'>"
            trades_table += """
<tr style='background-color: #f0f0f0;'>
    <th style='border: 1px solid #ddd; padding: 8px;'>Symbol</th>
    <th style='border: 1px solid #ddd; padding: 8px;'>Action</th>
    <th style='border: 1px solid #ddd; padding: 8px;'>Quantity</th>
    <th style='border: 1px solid #ddd; padding: 8px;'>Price</th>
    <th style='border: 1px solid #ddd; padding: 8px;'>P&L</th>
</tr>
            """

            for trade in trade_details[-20:]:  # 最近20笔
                pnl = trade.get('pnl', 0)
                pnl_color = 'green' if pnl > 0 else 'red' if pnl < 0 else 'black'

                trades_table += f"""
<tr>
    <td style='border: 1px solid #ddd; padding: 8px;'>{trade.get('symbol', 'N/A')}</td>
    <td style='border: 1px solid #ddd; padding: 8px;'>{trade.get('action', 'N/A')}</td>
    <td style='border: 1px solid #ddd; padding: 8px;'>{trade.get('quantity', 0)}</td>
    <td style='border: 1px solid #ddd; padding: 8px;'>Rs.{trade.get('price', 0):.2f}</td>
    <td style='border: 1px solid #ddd; padding: 8px; color: {pnl_color};'>Rs.{pnl:.2f}</td>
</tr>
                """

            trades_table += "</table>"

        subject = f"📊 Daily Trading Report - {datetime.now().strftime('%Y-%m-%d')}"

        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif;">
    <h1 style="color: #1976d2;">Daily Trading Report</h1>

    <div style="background-color: {'#e8f5e9' if daily_pnl > 0 else '#ffebee' if daily_pnl < 0 else '#f5f5f5'};
                padding: 20px; border-radius: 5px; margin: 20px 0;">
        <h2 style="margin: 0; color: {'#2e7d32' if daily_pnl > 0 else '#c62828' if daily_pnl < 0 else '#666'};">
            {'Profit' if daily_pnl > 0 else 'Loss' if daily_pnl < 0 else 'Break-even'}:
            Rs.{abs(daily_pnl):,.2f}
        </h2>
    </div>

    <table style="width: 100%; margin: 20px 0;">
        <tr>
            <td style="padding: 10px; background-color: #f5f5f5; border-radius: 3px; margin-bottom: 5px;">
                <strong>Total Trades:</strong> {total_trades}
            </td>
            <td style="padding: 10px; background-color: #f5f5f5; border-radius: 3px; margin-bottom: 5px;">
                <strong>Win Rate:</strong> {win_rate:.1f}%
            </td>
        </tr>
        <tr>
            <td style="padding: 10px; background-color: #f5f5f5; border-radius: 3px;">
                <strong>Avg Profit:</strong> Rs.{metrics.get('avg_profit', 0):,.2f}
            </td>
            <td style="padding: 10px; background-color: #f5f5f5; border-radius: 3px;">
                <strong>Avg Loss:</strong> Rs.{metrics.get('avg_loss', 0):,.2f}
            </td>
        </tr>
    </table>

    {trades_table}

    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">

    <p style="color: #999; font-size: 11px;">
        Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
        Agentic Trader System
    </p>
</body>
</html>
        """

        return self.send_email(subject, html_body, is_html=True)

    def test_connection(self) -> bool:
        """
        测试邮件连接

        Returns:
            是否连接成功
        """
        result = self.send_email(
            subject="✅ Email Connection Test",
            body="This is a test email from Agentic Trader System.\n\nEmail notifications are working correctly!"
        )

        return result.get("success", False)
