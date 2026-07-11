import { useEffect, useState } from 'react';
import { getPositions } from '../api';
import type { Position, OptionType } from '../types';
import { RefreshCw, AlertCircle, Wallet } from 'lucide-react';

const optionTypeLabels: Record<OptionType, string> = {
  european: '欧式',
  american: '美式',
  asian: '亚式',
  barrier: '障碍',
  lookback: '回望',
  binary: '二元',
  chooser: '选择',
  compound: '复合',
  forward_start: '远期生效',
  power: '幂',
  exchange: '交换',
  cliquet: '棘轮',
  shout: '喊价',
  double_barrier: '双边障碍',
  range: '区间',
  quanto: '数量调整',
  rainbow: '彩虹',
  spread: '价差',
  barrier_lookback: '障碍回望',
};

function formatNumber(value: number, decimals: number = 2): string {
  return value.toLocaleString('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export default function PositionsTable() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getPositions();
      setPositions(data);
    } catch (err) {
      setError('无法获取持仓数据，请确认后端服务已启动 (http://localhost:8000)');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // 汇总数据
  const totalNotional = positions.reduce((sum, p) => sum + p.notional, 0);
  const totalValue = positions.reduce((sum, p) => sum + p.current_value, 0);
  const longCount = positions.filter((p) => p.position_direction === 'long').length;
  const shortCount = positions.filter((p) => p.position_direction === 'short').length;

  return (
    <div className="p-6 space-y-5">
      {/* 工具栏 */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-t1">期权持仓总览</h3>
          <p className="text-xs text-t3 mt-1">共 {positions.length} 个持仓</p>
        </div>
        <button onClick={fetchData} disabled={loading} className="btn-secondary text-sm">
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          刷新
        </button>
      </div>

      {/* 汇总卡片 */}
      {!loading && !error && positions.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="card p-4">
            <p className="text-[11px] text-t3 uppercase tracking-wider mb-1">总名义本金</p>
            <p className="num text-xl font-bold text-t1">{formatNumber(totalNotional, 0)}</p>
            <p className="text-[10px] text-t4 mt-0.5">元</p>
          </div>
          <div className="card p-4">
            <p className="text-[11px] text-t3 uppercase tracking-wider mb-1">总当前估值</p>
            <p className="num text-xl font-bold text-gold">{formatNumber(totalValue, 0)}</p>
            <p className="text-[10px] text-t4 mt-0.5">元</p>
          </div>
          <div className="card p-4">
            <p className="text-[11px] text-t3 uppercase tracking-wider mb-1">多头持仓</p>
            <p className="num text-xl font-bold text-success">{longCount}</p>
            <p className="text-[10px] text-t4 mt-0.5">个</p>
          </div>
          <div className="card p-4">
            <p className="text-[11px] text-t3 uppercase tracking-wider mb-1">空头持仓</p>
            <p className="num text-xl font-bold text-warning">{shortCount}</p>
            <p className="text-[10px] text-t4 mt-0.5">个</p>
          </div>
        </div>
      )}

      {/* 加载状态 */}
      {loading && (
        <div className="card p-12 flex flex-col items-center justify-center gap-3">
          <div className="w-8 h-8 border-2 border-gold/30 border-t-gold rounded-full animate-spin" />
          <p className="text-sm text-t3">正在加载持仓数据...</p>
        </div>
      )}

      {/* 错误状态 */}
      {error && !loading && (
        <div className="card p-8 flex flex-col items-center justify-center gap-3 border-danger/30">
          <AlertCircle className="w-10 h-10 text-danger" />
          <p className="text-sm text-t2">{error}</p>
          <button onClick={fetchData} className="btn-secondary text-sm mt-2">
            <RefreshCw className="w-4 h-4" />
            重新加载
          </button>
        </div>
      )}

      {/* 空状态 */}
      {!loading && !error && positions.length === 0 && (
        <div className="card p-12 flex flex-col items-center justify-center gap-3">
          <Wallet className="w-10 h-10 text-t4" />
          <p className="text-sm text-t3">暂无持仓数据</p>
        </div>
      )}

      {/* 持仓表格 */}
      {!loading && !error && positions.length > 0 && (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line bg-elevated">
                  <th className="table-header text-left px-4 py-3">名称</th>
                  <th className="table-header text-left px-4 py-3">类型</th>
                  <th className="table-header text-left px-4 py-3">认购/认沽</th>
                  <th className="table-header text-left px-4 py-3">标的</th>
                  <th className="table-header text-right px-4 py-3">行权价</th>
                  <th className="table-header text-left px-4 py-3">到期日</th>
                  <th className="table-header text-right px-4 py-3">数量</th>
                  <th className="table-header text-center px-4 py-3">方向</th>
                  <th className="table-header text-right px-4 py-3">名义本金</th>
                  <th className="table-header text-right px-4 py-3">当前估值</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((pos) => (
                  <tr
                    key={pos.id}
                    className="border-b border-line hover:bg-hover transition-colors"
                  >
                    <td className="px-4 py-3 text-t1 font-medium">{pos.name}</td>
                    <td className="px-4 py-3">
                      <span className="tag border-line-soft text-t2">
                        {optionTypeLabels[pos.option_type]}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`tag ${pos.call_put === 'call' ? 'tag-call' : 'tag-put'}`}
                      >
                        {pos.call_put === 'call' ? '认购' : '认沽'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-t2">{pos.underlying_name}</td>
                    <td className="px-4 py-3 text-right num text-t1">
                      {formatNumber(pos.strike, 0)}
                    </td>
                    <td className="px-4 py-3 text-t2 num">{pos.maturity_date}</td>
                    <td className="px-4 py-3 text-right num text-t1">{pos.quantity}</td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`tag ${
                          pos.position_direction === 'long' ? 'tag-long' : 'tag-short'
                        }`}
                      >
                        {pos.position_direction === 'long' ? '多头' : '空头'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right num text-t2">
                      {formatNumber(pos.notional, 0)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex flex-col items-end">
                        <span className="num text-t1 font-semibold">
                          {formatNumber(pos.current_value, 0)}
                        </span>
                        <span className="text-[10px] text-t3">
                          成本: {formatNumber(pos.entry_price, 0)}
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
