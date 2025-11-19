# 测试文档

本文档介绍Agentic Trader的测试框架、如何运行测试以及如何编写新的测试。

## 目录

1. [测试架构](#测试架构)
2. [运行测试](#运行测试)
3. [测试覆盖率](#测试覆盖率)
4. [测试类型](#测试类型)
5. [编写新测试](#编写新测试)
6. [回测功能](#回测功能)

---

## 测试架构

项目使用 **pytest** 作为测试框架，包含以下组件：

```
agentic_trader/
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # 共享fixtures
│   ├── test_state.py            # 状态管理测试
│   ├── test_risk_manager.py     # 风险管理测试
│   ├── test_market_data.py      # 市场数据服务测试
│   ├── test_order_executor.py   # 订单执行测试
│   ├── test_indicators.py       # 技术指标测试
│   └── test_integration.py      # 集成测试
├── pytest.ini                   # pytest配置
└── pyproject.toml              # 依赖配置
```

### 关键特性

- ✅ **单元测试** - 测试单个组件
- ✅ **集成测试** - 测试组件协作
- ✅ **Mock对象** - 隔离外部依赖
- ✅ **覆盖率报告** - 代码覆盖率统计
- ✅ **并行执行** - 加速测试运行
- ✅ **自动化fixtures** - 简化测试设置

---

## 运行测试

### 基本用法

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest agentic_trader/tests/test_state.py

# 运行特定测试类
pytest agentic_trader/tests/test_state.py::TestTradeState

# 运行特定测试方法
pytest agentic_trader/tests/test_state.py::TestTradeState::test_update_pnl

# 详细输出
pytest -v

# 显示print输出
pytest -s

# 失败时进入调试器
pytest --pdb
```

### 使用标记运行测试

```bash
# 只运行单元测试
pytest -m unit

# 只运行集成测试
pytest -m integration

# 只运行风险管理测试
pytest -m risk

# 只运行快速测试（排除慢速测试）
pytest -m "not slow"

# 组合标记
pytest -m "unit and risk"
```

### 并行执行

```bash
# 使用所有CPU核心
pytest -n auto

# 使用4个进程
pytest -n 4
```

---

## 测试覆盖率

### 生成覆盖率报告

```bash
# 运行测试并生成覆盖率报告
pytest --cov=agentic_trader

# 显示缺失的行
pytest --cov=agentic_trader --cov-report=term-missing

# 生成HTML报告
pytest --cov=agentic_trader --cov-report=html

# 查看HTML报告
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### 覆盖率目标

| 组件 | 当前覆盖率 | 目标覆盖率 |
|------|-----------|-----------|
| TradeState | 95%+ | 100% |
| RiskManager | 90%+ | 95% |
| OrderExecutor | 90%+ | 95% |
| MarketDataService | 85%+ | 90% |
| IndicatorCalculator | 85%+ | 90% |
| **整体** | **90%+** | **95%** |

---

## 测试类型

### 1. 单元测试 (Unit Tests)

测试单个类或函数，使用Mock隔离外部依赖。

**示例**：`test_state.py`

```python
def test_update_pnl(trade_state):
    """测试盈亏更新"""
    trade_state.update_pnl(-500.0)
    assert trade_state.daily_pnl == -500.0
```

### 2. 集成测试 (Integration Tests)

测试多个组件协作，验证完整工作流。

**示例**：`test_integration.py`

```python
def test_full_trading_cycle_success(integrated_system):
    """测试完整交易周期"""
    # 1. 获取市场数据
    market_data = system["market_data"].fetch_all_market_data()

    # 2. 检查风险
    risk_check = system["risk_manager"].check_constraints("ICICIBANK", "BUY")

    # 3. 下单
    order_result = system["order_executor"].place_market_order(...)

    assert order_result["success"] is True
```

### 3. Mock测试

使用Mock对象模拟外部API调用。

**示例**：

```python
def test_fetch_quotes_success(market_data_service):
    """测试获取报价（成功）"""
    # Mock已在conftest.py中配置
    result = market_data_service.fetch_quotes("ICICIBANK")

    assert result["ltp"] == 1350.50
    assert result["volume"] == 1000000
```

---

## 编写新测试

### 使用Fixtures

在`conftest.py`中定义的fixtures可以在所有测试中使用：

```python
def test_my_feature(mock_openalgo_client, trade_state):
    """我的测试"""
    # mock_openalgo_client 和 trade_state 自动注入
    state.update_pnl(1000.0)
    assert state.daily_pnl == 1000.0
```

### 可用的Fixtures

| Fixture | 描述 |
|---------|------|
| `mock_openalgo_client` | Mock的OpenAlgo客户端 |
| `trade_state` | TradeState实例 |
| `test_config` | 测试配置字典 |
| `ist_timezone` | IST时区对象 |
| `sample_market_data` | 示例市场数据 |

### 添加新测试

1. **创建测试文件**：`test_<module_name>.py`

2. **定义测试类**：

```python
class TestMyFeature:
    """MyFeature测试套件"""

    @pytest.fixture
    def my_fixture(self):
        """创建测试所需的对象"""
        return MyFeature()

    def test_initialization(self, my_fixture):
        """测试初始化"""
        assert my_fixture is not None

    def test_feature_behavior(self, my_fixture):
        """测试功能行为"""
        result = my_fixture.do_something()
        assert result == expected_value
```

3. **添加测试标记**（可选）：

```python
@pytest.mark.unit
@pytest.mark.slow
def test_expensive_operation():
    """耗时测试"""
    pass
```

### 最佳实践

1. ✅ **一个测试一个断言** - 保持测试简单
2. ✅ **描述性测试名** - 清楚说明测试内容
3. ✅ **使用fixtures** - 避免重复代码
4. ✅ **Mock外部调用** - 隔离依赖
5. ✅ **测试边界情况** - 包括错误处理
6. ✅ **保持测试独立** - 测试之间不依赖
7. ✅ **快速运行** - 慢速测试使用`@pytest.mark.slow`

---

## 回测功能

### 回测引擎

位于 `agentic_trader/backtesting/engine.py`

**核心功能**：
- 模拟交易执行
- 计算手续费和滑点
- 跟踪持仓和权益
- 计算性能指标

### 性能指标

| 指标 | 描述 |
|------|------|
| **总收益率** | (最终资金 - 初始资金) / 初始资金 |
| **年化收益率** | 总收益率按年化计算 |
| **夏普比率** | 风险调整后收益 (>1为好，>2为优秀) |
| **最大回撤** | 权益曲线的最大下降幅度 |
| **胜率** | 获利交易占比 |
| **盈亏比** | 平均盈利 / 平均亏损 |

### 使用示例

```python
from agentic_trader.backtesting.engine import BacktestEngine

# 初始化引擎
engine = BacktestEngine(
    initial_capital=100000.0,
    commission_rate=0.0003,  # 0.03%
    slippage_rate=0.0005     # 0.05%
)

# 执行交易
engine.execute_trade(timestamp, symbol, 'BUY', quantity, price)

# 计算指标
result = engine.calculate_metrics()

print(f"总收益率: {result.total_return_pct:.2f}%")
print(f"夏普比率: {result.sharpe_ratio:.2f}")
print(f"最大回撤: {result.max_drawdown_pct:.2f}%")
```

### 可视化

位于 `agentic_trader/visualization/charts.py`

**生成图表**：
- 权益曲线
- 回撤分析
- 月度收益热力图

```python
from agentic_trader.visualization.charts import ChartGenerator

chart_gen = ChartGenerator(output_dir="results")

# 权益曲线
chart_gen.plot_equity_curve(
    equity_series=result.equity_curve,
    title="策略回测 - 权益曲线",
    filename="equity.png"
)

# 回撤分析
chart_gen.plot_drawdown(
    equity_series=result.equity_curve,
    title="策略回测 - 回撤分析",
    filename="drawdown.png"
)
```

### 完整示例

查看 `examples/run_backtest.py` 获取完整的回测示例。

```bash
python examples/run_backtest.py
```

---

## 持续集成 (CI)

### GitHub Actions

项目配置了GitHub Actions自动运行测试（如果有`.github/workflows/test.yml`）。

每次提交和PR时会自动：
1. 运行所有测试
2. 生成覆盖率报告
3. 检查代码质量

### 本地CI检查

运行与CI相同的检查：

```bash
# 运行测试
pytest

# 代码格式检查
ruff check .

# 类型检查
mypy agentic_trader

# 代码格式化
black agentic_trader
```

---

## 故障排除

### 常见问题

**问题**: `ModuleNotFoundError: No module named 'agentic_trader'`

**解决方案**: 在项目根目录运行：
```bash
pip install -e .
```

---

**问题**: 测试运行很慢

**解决方案**: 使用并行执行：
```bash
pytest -n auto
```

---

**问题**: Mock对象没有按预期工作

**解决方案**: 检查`conftest.py`中的fixture配置，确保Mock返回值正确。

---

## 资源

- [pytest文档](https://docs.pytest.org/)
- [pytest-cov文档](https://pytest-cov.readthedocs.io/)
- [unittest.mock文档](https://docs.python.org/3/library/unittest.mock.html)

---

## 贡献测试

欢迎贡献新的测试！请遵循以下准则：

1. 所有新功能必须包含测试
2. 测试覆盖率不应下降
3. 遵循现有的测试结构和命名约定
4. 添加适当的文档字符串
5. 确保所有测试通过

提交PR前运行：

```bash
pytest --cov=agentic_trader --cov-report=term-missing
```
