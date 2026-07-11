import { useEffect, useState } from 'react';
import { getRiskFactors } from '../api';
import type { RiskFactor } from '../types';
import {
  TrendingUp,
  Activity,
  Percent,
  RefreshCw,
  AlertCircle,
  Database,
  Server,
} from 'lucide-react';

// 格式化数字
function formatNumber(value: number, decimals: number = 2): string {
  return value.toLocaleString('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

// 数据卡片
interface DataCardProps {
  title: string;
  value: number;
  unit: string;
  icon: typeof TrendingUp;
  color: string;
  bgColor: string;
  description: string;
  decimals?: number;
}

function DataCard({
  title,
  value,
  unit,
  icon: Icon,
  color,
  bgColor,
  description,
  decimals = 2,
}: DataCardProps) {
  return (
    <div className="card p-6 hover:border-line-soft transition-all duration-200">
      <div className="flex items-start justify-between mb-5">
        <div>
          <p className="text-xs text-t3 uppercase tracking-wider mb-1">{title}</p>
          <p className="text-[11px] text-t4">{description}</p>
        </div>
        <div
          className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ backgroundColor: bgColor }}
        >
          <Icon className="w-5 h-5" style={{ color }} />
        </div>
      </div>
      <div className="flex items-baseline gap-2">
        <span className="num text-3xl font-bold text-t1">{formatNumber(value, decimals)}</span>
        <span className="text-sm text-t3">{unit}</span>
      </div>
    </div>
  );
}

export default function MarketData() {
  const [riskFactors, setRiskFactors] = useState<RiskFactor | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getRiskFactors();
      setRiskFactors(data);
    } catch (err) {
      setError('无法连接到后端服务，请确认服务已启动 (http://localhost:8000)');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <div className="p-6 space-y-6 max-w-6xl">
      {/* 工具栏 */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-t1">市场风险因子</h3>
          <p className="text-xs text-t3 mt-1">当前市场环境下的核心风险因子数据</p>
        </div>
        <button onClick={fetchData} disabled={loading} className="btn-secondary text-sm">
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          刷新数据
        </button>
      </div>

      {/* 加载状态 */}
      {loading && (
        <div className="card p-12 flex flex-col items-center justify-center gap-3">
          <div className="w-8 h-8 border-2 border-gold/30 border-t-gold rounded-full animate-spin" />
          <p className="text-sm text-t3">正在获取市场数据...</p>
        </div>
      )}

      {/* 错误状态 */}
      {error && !loading && (
        <div className="card p-8 flex flex-col items-center justify-center gap-3 border-danger/30">
          <AlertCircle className="w-10 h-10 text-danger" />
          <p className="text-sm text-t2">{error}</p>
          <button onClick={fetchData} className="btn-secondary text-sm mt-2">
            <RefreshCw className="w-4 h-4" />
            重新连接
          </button>
        </div>
      )}

      {/* 数据卡片 */}
      {riskFactors && !loading && !error && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <DataCard
              title="中证500指数"
              value={riskFactors.index_price}
              unit="点"
              icon={TrendingUp}
              color="#f0b90b"
              bgColor="rgba(240, 185, 11, 0.1)"
              description="标的指数当前价格"
              decimals={2}
            />
            <DataCard
              title="年化波动率"
              value={riskFactors.volatility}
              unit=""
              icon={Activity}
              color="#00d4ff"
              bgColor="rgba(0, 212, 255, 0.1)"
              description="标的资产年化波动率"
              decimals={4}
            />
            <DataCard
              title="国债收益率"
              value={riskFactors.risk_free_rate}
              unit=""
              icon={Percent}
              color="#3b82f6"
              bgColor="rgba(59, 130, 246, 0.1)"
              description="无风险利率（年化）"
              decimals={4}
            />
          </div>

          {/* 附加信息 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
            <div className="card p-5">
              <div className="flex items-center gap-2 mb-4">
                <Database className="w-4 h-4 text-t3" />
                <h4 className="text-sm font-medium text-t2">数据来源</h4>
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between py-2 border-b border-line">
                  <span className="text-xs text-t3">数据接口</span>
                  <span className="num text-xs text-t1">/api/risk-factors</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-line">
                  <span className="text-xs text-t3">更新频率</span>
                  <span className="text-xs text-t1">实时</span>
                </div>
                <div className="flex items-center justify-between py-2">
                  <span className="text-xs text-t3">数据状态</span>
                  <span className="text-xs text-success flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-success" />
                    正常
                  </span>
                </div>
              </div>
            </div>

            <div className="card p-5">
              <div className="flex items-center gap-2 mb-4">
                <Server className="w-4 h-4 text-t3" />
                <h4 className="text-sm font-medium text-t2">服务状态</h4>
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between py-2 border-b border-line">
                  <span className="text-xs text-t3">后端服务</span>
                  <span className="text-xs text-success flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-success" />
                    运行中
                  </span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-line">
                  <span className="text-xs text-t3">API 延迟</span>
                  <span className="num text-xs text-t1">{'<'} 50ms</span>
                </div>
                <div className="flex items-center justify-between py-2">
                  <span className="text-xs text-t3">最后更新</span>
                  <span className="num text-xs text-t1">
                    {new Date().toLocaleTimeString('zh-CN', { hour12: false })}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
