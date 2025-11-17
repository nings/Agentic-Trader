"""规范化日志系统"""

import logging
import logging.handlers
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器（JSON格式）"""

    def format(self, record: logging.LogRecord) -> str:
        """
        格式化日志记录为JSON

        Args:
            record: 日志记录

        Returns:
            JSON格式的日志字符串
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # 添加额外字段
        if hasattr(record, 'symbol'):
            log_data['symbol'] = record.symbol
        if hasattr(record, 'order_id'):
            log_data['order_id'] = record.order_id
        if hasattr(record, 'action'):
            log_data['action'] = record.action

        # 添加异常信息
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """带颜色的控制台格式化器"""

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        """
        格式化日志记录（带颜色）

        Args:
            record: 日志记录

        Returns:
            带颜色的日志字符串
        """
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    enable_console: bool = True,
    enable_structured: bool = False
) -> None:
    """
    配置日志系统

    Args:
        log_level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        log_dir: 日志目录
        enable_console: 是否输出到控制台
        enable_structured: 是否使用结构化日志（JSON）
    """
    # 创建日志目录
    Path(log_dir).mkdir(exist_ok=True)

    # 根logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 清除现有处理器
    root_logger.handlers.clear()

    # 控制台处理器（带颜色）
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        if enable_structured:
            console_formatter = StructuredFormatter()
        else:
            console_formatter = ColoredFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # 文件处理器（按天轮转）
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=f"{log_dir}/trading.log",
        when='midnight',
        interval=1,
        backupCount=30,  # 保留30天
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)

    if enable_structured:
        file_handler.setFormatter(StructuredFormatter())
    else:
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))

    root_logger.addHandler(file_handler)

    # 错误日志单独文件
    error_handler = logging.handlers.RotatingFileHandler(
        filename=f"{log_dir}/errors.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(StructuredFormatter() if enable_structured else logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    root_logger.addHandler(error_handler)

    # 审计日志（独立logger）
    audit_logger = logging.getLogger('audit')
    audit_logger.setLevel(logging.INFO)
    audit_handler = logging.handlers.RotatingFileHandler(
        filename=f"{log_dir}/audit.log",
        maxBytes=50*1024*1024,  # 50MB
        backupCount=10,
        encoding='utf-8'
    )
    audit_handler.setFormatter(StructuredFormatter())
    audit_logger.addHandler(audit_handler)
    audit_logger.propagate = False  # 不传播到root logger

    # 记录日志系统启动
    logger = logging.getLogger(__name__)
    logger.info(f"Logging system initialized - Level: {log_level}, Dir: {log_dir}")


def get_logger(name: str) -> logging.Logger:
    """
    获取logger实例

    Args:
        name: logger名称

    Returns:
        Logger实例
    """
    return logging.getLogger(name)
