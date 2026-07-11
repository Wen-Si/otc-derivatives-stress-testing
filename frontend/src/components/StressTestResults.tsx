import type { StressTestResponse, Shock, FactorType } from '../types';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import {
  Download,
  TrendingDown,
  TrendingUp,
  Activity,
  Percent,
  Zap,
  BarChart3,
  FileText,
} from 'lucide-react';

// ============================================
// 辅助函数
// ============================================

function formatNumber(value: number, decimals: number = 2): string {
  return value.toLocaleString('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function formatPct(value: number, decimals: number = 2): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

function formatShockValue(shock: Shock): string {
  const sign = shock.shock_value >= 0 ? '+' : '';
  if (shock.shock_type === 'relative') {
    return `${sign}${(shock.shock_value * 100).toFixed(2)}%`;
  }
  if (shock.factor_type === 'risk_free_rate') {
    return `${sign}${(shock.shock_value * 10000).toFixed(1)} bp`;
  }
  return `${sign}${(shock.shock_value * 100).toFixed(2)}%`;
}

function getFactorTypeLabel(type: FactorType): string {
  switch (type) {
    case 'price':
      return '价格';
    case 'volatility':
      return '波动率';
    case 'risk_free_rate':
      return '无风险利率';
    default:
      return type;
  }
}

function getShockColor(shock: Shock): string {
  if (shock.factor_type === 'price') {
    return shock.shock_value < 0 ? '#ff4757' : '#00c853';
  }
  return '#00d4ff';
}

// 自定义图表 Tooltip
interface TooltipProps {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: TooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="card-elevated p-3 text-xs border-gold/20">
      <p className="text-t1 font-medium mb-2">{label}</p>
      {payload.map((entry, idx) => (
        <div key={idx} className="flex items-center gap-2 py-0.5">
          <span
            className="w-2 h-2 rounded-sm"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-t3">{entry.name}</span>
          <span className="num text-t1 ml-auto">{formatNumber(entry.value, 0)}</span>
        </div>
      ))}
    </div>
  );
}

// ============================================
// 空状态
// ============================================

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full min-h-[400px] gap-4">
      <div className="w-16 h-16 rounded-full bg-elevated flex items-center justify-center">
        <BarChart3 className="w-8 h-8 text-t4" />
      </div>
      <div className="text-center">
        <h3 className="text-base font-medium text-t2 mb-1">暂无压力测试结果</h3>
        <p className="text-sm text-t3">请前往「AI压力交互」页面，描述压力场景并执行测试</p>
      </div>
    </div>
  );
}

// ============================================
// 主组件
// ============================================

export default function StressTestResults({ result }: { result: StressTestResponse | null }) {
  if (!result) {
    return <EmptyState />;
  }

  const isProfit = result.total_pnl >= 0;

  // 图表数据
  const chartData = result.results.map((r) => ({
    name: r.position_name,
    压力前估值: r.original_value,
    压力后估值: r.stressed_value,
  }));

  // 导出报告 (CSV)
  const handleExport = () => {
    const csv = [
      ['持仓名称', '压力前估值', '压力后估值', '盈亏变化', '盈亏百分比'],
      ...result.results.map((r) => [
        r.position_name,
        r.original_value.toString(),
        r.stressed_value.toString(),
        r.pnl_change.toString(),
        `${(r.pnl_pct * 100).toFixed(2)}%`,
      ]),
    ];
    const csvContent = csv.map((row) => row.map((c) => `"${c}"`).join(',')).join('\n');
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `压力测试报告_${result.scenario_name}_${new Date()
      .toISOString()
      .slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-6 space-y-5">
      {/* 顶部操作栏 */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-t1">压力测试分析报告</h3>
          <p className="text-xs text-t3 mt-1">场景: {result.scenario_name}</p>
        </div>
        <button onClick={handleExport} className="btn-secondary text-sm">
          <Download className="w-4 h-4" />
          导出报告
        </button>
      </div>

      {/* 场景摘要卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className={`card p-5 ${isProfit ? 'border-success/30' : 'border-danger/30'}`}>
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs text-t3 uppercase tracking-wider">总盈亏</p>
            {isProfit ? (
              <TrendingUp className="w-5 h-5 text-success" />
            ) : (
              <TrendingDown className="w-5 h-5 text-danger" />
            )}
          </div>
          <p className={`num text-2xl font-bold ${isProfit ? 'text-success' : 'text-danger'}`}>
            {result.total_pnl >= 0 ? '+' : ''}
            {formatNumber(result.total_pnl, 0)}
          </p>
          <p className="text-xs text-t4 mt-1">元</p>
        </div>

        <div className={`card p-5 ${isProfit ? 'border-success/30' : 'border-danger/30'}`}>
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs text-t3 uppercase tracking-wider">盈亏百分比</p>
            <Percent className="w-5 h-5 text-t3" />
          </div>
          <p className={`num text-2xl font-bold ${isProfit ? 'text-success' : 'text-danger'}`}>
            {result.total_pnl_pct >= 0 ? '+' : ''}
            {formatPct(result.total_pnl_pct)}
          </p>
          <p className="text-xs text-t4 mt-1">相对压力前估值</p>
        </div>

        <div className="card p-5">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs text-t3 uppercase tracking-wider">受影响持仓</p>
            <Activity className="w-5 h-5 text-t3" />
          </div>
          <p className="num text-2xl font-bold text-t1">{result.results.length}</p>
          <p className="text-xs text-t4 mt-1">个持仓</p>
        </div>
      </div>

      {/* 风险因子冲击明细表 */}
      <div className="card p-5">
        <div className="flex items-center gap-2 mb-4">
          <Zap className="w-4 h-4 text-gold" />
          <h4 className="text-sm font-medium text-t1">风险因子冲击明细</h4>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line">
                <th className="table-header text-left py-2 pr-4">因子名称</th>
                <th className="table-header text-left py-2 pr-4">类型</th>
                <th className="table-header text-left py-2 pr-4">冲击方式</th>
                <th className="table-header text-right py-2 pr-4">冲击值</th>
                <th className="table-header text-left py-2">描述</th>
              </tr>
            </thead>
            <tbody>
              {result.shocks.map((shock, idx) => (
                <tr key={idx} className="border-b border-line hover:bg-hover transition-colors">
                  <td className="py-2.5 pr-4 text-t1 font-medium">{shock.factor_name}</td>
                  <td className="py-2.5 pr-4 text-t2">
                    {getFactorTypeLabel(shock.factor_type)}
                  </td>
                  <td className="py-2.5 pr-4 text-t2">
                    {shock.shock_type === 'relative' ? '相对' : '绝对'}
                  </td>
                  <td
                    className="py-2.5 pr-4 text-right num font-semibold"
                    style={{ color: getShockColor(shock) }}
                  >
                    {formatShockValue(shock)}
                  </td>
                  <td className="py-2.5 text-t3 text-xs">{shock.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 柱状图 */}
      <div className="card p-5">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 className="w-4 h-4 text-gold" />
          <h4 className="text-sm font-medium text-t1">各持仓估值变化对比</h4>
        </div>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1a2535" vertical={false} />
            <XAxis
              dataKey="name"
              tick={{ fill: '#5d6b7e', fontSize: 11 }}
              tickLine={{ stroke: '#1a2535' }}
              axisLine={{ stroke: '#1a2535' }}
              interval={0}
              angle={-15}
              textAnchor="end"
              height={60}
            />
            <YAxis
              tick={{ fill: '#5d6b7e', fontSize: 11 }}
              tickLine={{ stroke: '#1a2535' }}
              axisLine={{ stroke: '#1a2535' }}
              tickFormatter={(v) =>
                v >= 10000 ? `${(v / 10000).toFixed(0)}万` : v.toString()
              }
            />
            <Tooltip
              content={<CustomTooltip />}
              cursor={{ fill: 'rgba(240, 185, 11, 0.05)' }}
            />
            <Legend
              wrapperStyle={{ fontSize: 12, color: '#9fb0c3', paddingTop: 10 }}
              iconType="square"
            />
            <Bar
              dataKey="压力前估值"
              fill="#3b82f6"
              radius={[4, 4, 0, 0]}
              maxBarSize={40}
            />
            <Bar
              dataKey="压力后估值"
              fill="#f0b90b"
              radius={[4, 4, 0, 0]}
              maxBarSize={40}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* P&L 分解表 */}
      <div className="card p-5">
        <div className="flex items-center gap-2 mb-4">
          <FileText className="w-4 h-4 text-gold" />
          <h4 className="text-sm font-medium text-t1">持仓级 P&L 分解</h4>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line">
                <th className="table-header text-left py-2 pr-4">持仓名称</th>
                <th className="table-header text-right py-2 pr-4">压力前估值</th>
                <th className="table-header text-right py-2 pr-4">压力后估值</th>
                <th className="table-header text-right py-2 pr-4">盈亏变化</th>
                <th className="table-header text-right py-2">盈亏百分比</th>
              </tr>
            </thead>
            <tbody>
              {result.results.map((r) => {
                const profit = r.pnl_change >= 0;
                return (
                  <tr
                    key={r.position_id}
                    className="border-b border-line hover:bg-hover transition-colors"
                  >
                    <td className="py-2.5 pr-4 text-t1 font-medium">{r.position_name}</td>
                    <td className="py-2.5 pr-4 text-right num text-t2">
                      {formatNumber(r.original_value, 0)}
                    </td>
                    <td className="py-2.5 pr-4 text-right num text-t2">
                      {formatNumber(r.stressed_value, 0)}
                    </td>
                    <td
                      className={`py-2.5 pr-4 text-right num font-semibold ${
                        profit ? 'text-success' : 'text-danger'
                      }`}
                    >
                      {profit ? '+' : ''}
                      {formatNumber(r.pnl_change, 0)}
                    </td>
                    <td
                      className={`py-2.5 text-right num font-semibold ${
                        profit ? 'text-success' : 'text-danger'
                      }`}
                    >
                      {profit ? '+' : ''}
                      {formatPct(r.pnl_pct)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
