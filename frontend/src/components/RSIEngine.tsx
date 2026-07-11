import { useEffect, useState, useCallback } from 'react';
import { getRSIStatus, getRSIHistory, runRSI } from '../api';
import type { RSIStatus, RSIEpoch, RSIRunResult } from '../types';
import {
  BrainCircuit,
  Play,
  RefreshCw,
  TrendingDown,
  Target,
  Gauge,
  CheckCircle2,
  AlertCircle,
  Cpu,
  Layers,
  Zap,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react';

// 格式化数字
function fmt(value: number | null | undefined, decimals: number = 4): string {
  if (value === null || value === undefined) return '--';
  return value.toLocaleString('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function fmtPct(value: number | null | undefined): string {
  if (value === null || value === undefined) return '--';
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

// 期权类型中文名
const OPTION_TYPE_NAMES: Record<string, string> = {
  european: '欧式',
  american: '美式',
  asian: '亚式',
  barrier: '障碍',
  lookback: '回望',
};

// 参数中文名
const PARAM_NAMES: Record<string, string> = {
  american_steps: '美式二叉树步数',
  asian_n_simulations: '亚式蒙特卡洛次数',
  barrier_n_simulations: '障碍蒙特卡洛次数',
  lookback_n_simulations: '回望蒙特卡洛次数',
};

export default function RSIEngine() {
  const [status, setStatus] = useState<RSIStatus | null>(null);
  const [history, setHistory] = useState<RSIEpoch[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<RSIRunResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [maxIter, setMaxIter] = useState(3);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [st, hist] = await Promise.all([getRSIStatus(), getRSIHistory()]);
      setStatus(st);
      setHistory(hist.epochs || []);
    } catch (err) {
      setError('无法连接到后端服务，请确认服务已启动');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleRunRSI = async () => {
    setRunning(true);
    setError(null);
    setRunResult(null);
    try {
      const result = await runRSI(maxIter);
      setRunResult(result);
      // 刷新数据
      await fetchData();
    } catch (err: any) {
      setError(`RSI训练失败: ${err?.message || '未知错误'}`);
    } finally {
      setRunning(false);
    }
  };

  // MAE 趋势图数据
  const maeData = history.map((e) => e.mae).filter((v) => v !== null && v !== undefined) as number[];
  const maxMae = maeData.length > 0 ? Math.max(...maeData) : 1;
  const minMae = maeData.length > 0 ? Math.min(...maeData) : 0;
  const maeRange = maxMae - minMae || 1;

  // 收敛趋势图
  const convergenceData = history.map((e) => ({
    epoch: e.epoch,
    mae: e.mae,
    mape: e.mape,
    r2: e.r_squared,
  }));

  return (
    <div className="p-6 space-y-5 max-w-7xl">
      {/* ============ 顶部操作栏 ============ */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-t1 flex items-center gap-2">
            <BrainCircuit className="w-5 h-5 text-gold" />
            递归自我提升引擎
          </h3>
          <p className="text-xs text-t3 mt-1">
            引擎通过自我评估、参数优化、知识积累的递归循环，持续提升定价精度
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <label className="text-xs text-t3">迭代次数</label>
            <select
              value={maxIter}
              onChange={(e) => setMaxIter(Number(e.target.value))}
              disabled={running}
              className="bg-elevated border border-line-soft text-t1 text-xs rounded-md px-3 py-1.5 focus:border-gold/50 transition-colors"
            >
              <option value={1}>1轮</option>
              <option value={3}>3轮</option>
              <option value={5}>5轮</option>
              <option value={10}>10轮</option>
            </select>
          </div>
          <button
            onClick={handleRunRSI}
            disabled={running}
            className="btn-primary text-sm"
          >
            {running ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                训练中...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                启动RSI训练
              </>
            )}
          </button>
          <button onClick={fetchData} disabled={loading} className="btn-secondary text-sm">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </button>
        </div>
      </div>

      {/* ============ 加载状态 ============ */}
      {loading && !status && (
        <div className="card p-12 flex flex-col items-center justify-center gap-3">
          <div className="w-8 h-8 border-2 border-gold/30 border-t-gold rounded-full animate-spin" />
          <p className="text-sm text-t3">正在加载RSI引擎状态...</p>
        </div>
      )}

      {/* ============ 错误状态 ============ */}
      {error && !loading && (
        <div className="card p-8 flex flex-col items-center justify-center gap-3 border-danger/30">
          <AlertCircle className="w-10 h-10 text-danger" />
          <p className="text-sm text-t2">{error}</p>
          <button onClick={fetchData} className="btn-secondary text-sm mt-2">
            <RefreshCw className="w-4 h-4" />
            重试
          </button>
        </div>
      )}

      {/* ============ 训练进度提示 ============ */}
      {running && (
        <div className="card p-6 border-gold/30 glow-gold">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 border-2 border-gold/30 border-t-gold rounded-full animate-spin" />
            <div>
              <p className="text-sm font-medium text-gold">RSI训练进行中</p>
              <p className="text-xs text-t3 mt-0.5">
                正在生成测试样本并用高精度基准评估模型误差（可能需要1-3分钟）...
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-xs text-t3">
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-gold animate-pulse" />
              生成6种市场场景测试样本
            </span>
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-glow animate-pulse" />
              50万次蒙特卡洛基准计算
            </span>
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
              EWMA参数优化
            </span>
          </div>
        </div>
      )}

      {/* ============ 训练结果 ============ */}
      {runResult && !running && (
        <div className="card p-6 border-success/30 animate-fade-in">
          <div className="flex items-center gap-2 mb-4">
            <CheckCircle2 className="w-5 h-5 text-success" />
            <h4 className="text-sm font-semibold text-t1">RSI训练完成</h4>
            {runResult.converged && (
              <span className="tag text-success border-success/40 bg-success/10 ml-2">
                已收敛
              </span>
            )}
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-elevated rounded-lg p-4">
              <div className="flex items-center gap-1.5 mb-2">
                <Layers className="w-3.5 h-3.5 text-t3" />
                <span className="text-xs text-t3">迭代轮数</span>
              </div>
              <span className="num text-2xl font-bold text-t1">{runResult.n_iterations}</span>
            </div>
            <div className="bg-elevated rounded-lg p-4">
              <div className="flex items-center gap-1.5 mb-2">
                <TrendingDown className="w-3.5 h-3.5 text-success" />
                <span className="text-xs text-t3">MAE总提升</span>
              </div>
              <span className="num text-2xl font-bold text-success">
                {fmtPct(runResult.total_improvement_pct)}
              </span>
            </div>
            <div className="bg-elevated rounded-lg p-4">
              <div className="flex items-center gap-1.5 mb-2">
                <Target className="w-3.5 h-3.5 text-cyan-glow" />
                <span className="text-xs text-t3">初始MAE</span>
              </div>
              <span className="num text-2xl font-bold text-t2">
                {fmt(runResult.initial_metrics.mae)}
              </span>
            </div>
            <div className="bg-elevated rounded-lg p-4">
              <div className="flex items-center gap-1.5 mb-2">
                <Target className="w-3.5 h-3.5 text-gold" />
                <span className="text-xs text-t3">最终MAE</span>
              </div>
              <span className="num text-2xl font-bold text-gold">
                {fmt(runResult.final_metrics.mae)}
              </span>
            </div>
          </div>
          {/* 逐轮迭代对比 */}
          {runResult.iterations.length > 1 && (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="table-header border-b border-line">
                    <th className="text-left py-2 px-3">轮次</th>
                    <th className="text-right py-2 px-3">MAE</th>
                    <th className="text-right py-2 px-3">RMSE</th>
                    <th className="text-right py-2 px-3">MAPE</th>
                    <th className="text-right py-2 px-3">R²</th>
                    <th className="text-right py-2 px-3">提升</th>
                    <th className="text-center py-2 px-3">状态</th>
                  </tr>
                </thead>
                <tbody>
                  {runResult.iterations.map((it, idx) => (
                    <tr key={idx} className="border-b border-line/50 hover:bg-hover/30 transition-colors">
                      <td className="py-2 px-3 text-t2 font-medium">Epoch {it.epoch}</td>
                      <td className="py-2 px-3 text-right num text-t1">{fmt(it.metrics.mae)}</td>
                      <td className="py-2 px-3 text-right num text-t2">{fmt(it.metrics.rmse)}</td>
                      <td className="py-2 px-3 text-right num text-t2">{fmt(it.metrics.mape, 2)}%</td>
                      <td className="py-2 px-3 text-right num text-t2">{fmt(it.metrics.r_squared, 6)}</td>
                      <td className="py-2 px-3 text-right num">
                        <span className={it.improvement_pct > 0 ? 'text-success' : 'text-t3'}>
                          {fmtPct(it.improvement_pct)}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-center">
                        {it.converged ? (
                          <span className="text-success text-xs">已收敛</span>
                        ) : (
                          <span className="text-t4 text-xs">优化中</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ============ 状态概览卡片 ============ */}
      {status && !loading && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <MetricCard
              title="总迭代轮次"
              value={status.total_epochs.toString()}
              icon={Layers}
              color="#f0b90b"
              bgColor="rgba(240, 185, 11, 0.1)"
              subtitle={status.is_active ? '引擎已激活' : '尚未训练'}
            />
            <MetricCard
              title="最新MAE"
              value={fmt(status.latest_mae)}
              icon={Target}
              color="#00d4ff"
              bgColor="rgba(0, 212, 255, 0.1)"
              subtitle="平均绝对误差"
            />
            <MetricCard
              title="最新MAPE"
              value={status.latest_mape !== null ? `${fmt(status.latest_mape, 2)}%` : '--'}
              icon={Gauge}
              color="#3b82f6"
              bgColor="rgba(59, 130, 246, 0.1)"
              subtitle="平均绝对百分比误差"
            />
            <MetricCard
              title="R² 拟合优度"
              value={fmt(status.latest_r_squared, 6)}
              icon={CheckCircle2}
              color={status.latest_r_squared !== null && status.latest_r_squared > 0.99 ? '#00c853' : '#ffa726'}
              bgColor="rgba(0, 200, 83, 0.1)"
              subtitle="越接近1越好"
            />
            <MetricCard
              title="引擎状态"
              value={status.is_using_default ? '默认参数' : status.latest_converged ? '已收敛' : '已优化'}
              icon={status.is_using_default ? Cpu : (status.latest_converged ? CheckCircle2 : Zap)}
              color={status.is_using_default ? '#5d6b7e' : (status.latest_converged ? '#00c853' : '#f0b90b')}
              bgColor={status.is_using_default ? 'rgba(93, 107, 126, 0.1)' : (status.latest_converged ? 'rgba(0, 200, 83, 0.1)' : 'rgba(240, 185, 11, 0.1)')}
              subtitle={status.is_using_default ? '未执行RSI训练' : `最近提升 ${fmtPct(status.latest_improvement_pct)}`}
            />
          </div>

          {/* ============ 精度进化趋势图 ============ */}
          {convergenceData.length > 0 && (
            <div className="card p-5">
              <div className="flex items-center gap-2 mb-4">
                <TrendingDown className="w-4 h-4 text-gold" />
                <h4 className="text-sm font-medium text-t1">精度进化趋势</h4>
                <span className="text-xs text-t4 ml-2">MAE越低越好</span>
              </div>
              <MAEChart data={convergenceData} />
            </div>
          )}

          {/* ============ 当前模型参数 + 校准系数 ============ */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* 模型参数 */}
            <div className="card p-5">
              <div className="flex items-center gap-2 mb-4">
                <Cpu className="w-4 h-4 text-cyan-glow" />
                <h4 className="text-sm font-medium text-t1">当前模型参数</h4>
                {status.is_using_default && (
                  <span className="tag text-t3 border-line-soft bg-elevated ml-2">默认值</span>
                )}
              </div>
              <div className="space-y-2">
                {Object.entries(status.current_model_params).map(([key, val]) => (
                  <div key={key} className="flex items-center justify-between py-2 border-b border-line/50">
                    <span className="text-xs text-t3">{PARAM_NAMES[key] || key}</span>
                    <span className="num text-sm text-t1 font-medium">{val.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* 校准系数 */}
            <div className="card p-5">
              <div className="flex items-center gap-2 mb-4">
                <Gauge className="w-4 h-4 text-gold" />
                <h4 className="text-sm font-medium text-t1">校准系数</h4>
                <span className="text-xs text-t4 ml-2">校正系统性偏差</span>
              </div>
              <div className="space-y-2">
                {Object.entries(status.current_calibration).map(([key, val]) => {
                  const drift = val - 1.0;
                  return (
                    <div key={key} className="flex items-center justify-between py-2 border-b border-line/50">
                      <span className="text-xs text-t3">{OPTION_TYPE_NAMES[key] || key}期权</span>
                      <div className="flex items-center gap-2">
                        <span className="num text-sm text-t1 font-medium">{fmt(val, 6)}</span>
                        {Math.abs(drift) > 0.001 ? (
                          <span className={`text-xs flex items-center ${drift > 0 ? 'text-success' : 'text-warning'}`}>
                            {drift > 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                            {fmtPct(drift * 100)}
                          </span>
                        ) : (
                          <span className="text-xs text-t4">无偏差</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* ============ RSI迭代历史表 ============ */}
          {history.length > 0 && (
            <div className="card p-5">
              <div className="flex items-center gap-2 mb-4">
                <Layers className="w-4 h-4 text-t3" />
                <h4 className="text-sm font-medium text-t1">RSI迭代历史</h4>
                <span className="text-xs text-t4 ml-2">共 {history.length} 轮</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="table-header border-b border-line">
                      <th className="text-left py-2.5 px-3">轮次</th>
                      <th className="text-left py-2.5 px-3">名称</th>
                      <th className="text-right py-2.5 px-3">MAE</th>
                      <th className="text-right py-2.5 px-3">RMSE</th>
                      <th className="text-right py-2.5 px-3">MAPE</th>
                      <th className="text-right py-2.5 px-3">R²</th>
                      <th className="text-right py-2.5 px-3">最大误差</th>
                      <th className="text-right py-2.5 px-3">提升</th>
                      <th className="text-center py-2.5 px-3">收敛</th>
                      <th className="text-right py-2.5 px-3">样本数</th>
                      <th className="text-right py-2.5 px-3">时间</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((e, idx) => (
                      <tr
                        key={e.id}
                        className={`border-b border-line/30 hover:bg-hover/30 transition-colors ${
                          idx === history.length - 1 ? 'bg-gold/5' : ''
                        }`}
                      >
                        <td className="py-2.5 px-3">
                          <span className="num text-t2 font-medium">{e.epoch}</span>
                        </td>
                        <td className="py-2.5 px-3 text-t2">{e.name}</td>
                        <td className="py-2.5 px-3 text-right num text-t1">{fmt(e.mae)}</td>
                        <td className="py-2.5 px-3 text-right num text-t2">{fmt(e.rmse)}</td>
                        <td className="py-2.5 px-3 text-right num text-t2">{fmt(e.mape, 2)}%</td>
                        <td className="py-2.5 px-3 text-right num text-t2">{fmt(e.r_squared, 6)}</td>
                        <td className="py-2.5 px-3 text-right num text-warning">{fmt(e.max_error)}</td>
                        <td className="py-2.5 px-3 text-right num">
                          {e.epoch === 0 ? (
                            <span className="text-t4">基线</span>
                          ) : (
                            <span className={e.improvement_pct > 0 ? 'text-success' : 'text-t3'}>
                              {fmtPct(e.improvement_pct)}
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-center">
                          {e.converged ? (
                            <CheckCircle2 className="w-4 h-4 text-success mx-auto" />
                          ) : (
                            <span className="text-t4">--</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-right num text-t3">{e.n_samples}</td>
                        <td className="py-2.5 px-3 text-right text-t4 text-[10px]">{e.created_at}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ============ RSI流程说明 ============ */}
          {history.length === 0 && !running && (
            <div className="card p-8">
              <div className="flex items-center gap-2 mb-4">
                <BrainCircuit className="w-5 h-5 text-gold" />
                <h4 className="text-sm font-semibold text-t1">RSI递归自我提升工作原理</h4>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <FlowStep
                  step="01"
                  title="自我评估"
                  desc="生成6种市场场景(基准/温和下跌/严重下跌/极端下跌/温和上涨/快速上涨)的测试样本，用高精度基准对比当前模型预测误差"
                  icon={Target}
                  color="#00d4ff"
                />
                <FlowStep
                  step="02"
                  title="参数优化"
                  desc="基于误差自动调整蒙特卡洛模拟次数、二叉树步数，并通过EWMA算法计算校准系数校正系统性偏差"
                  icon={Cpu}
                  color="#f0b90b"
                />
                <FlowStep
                  step="03"
                  title="知识积累"
                  desc="将优化后的参数与校准系数持久化到数据库，形成不断进化的知识库，供后续压力测试使用"
                  icon={Layers}
                  color="#3b82f6"
                />
                <FlowStep
                  step="04"
                  title="递归提升"
                  desc="重复评估-优化循环，直到精度提升幅度低于2%收敛阈值，实现自我进化"
                  icon={Zap}
                  color="#00c853"
                />
              </div>
              <div className="mt-6 p-4 bg-elevated rounded-lg border border-line-soft">
                <p className="text-xs text-t3 leading-relaxed">
                  <span className="text-gold font-medium">高精度基准策略：</span>
                  欧式期权使用BSM解析解（精确解）；美式期权使用2000步CRR二叉树；亚式（算术）、障碍、回望期权使用50万次蒙特卡洛模拟作为基准。当前生产模型使用2万次蒙特卡洛和200步二叉树以平衡精度与性能。
                </p>
                <p className="text-xs text-t3 leading-relaxed mt-2">
                  <span className="text-gold font-medium">集成效果：</span>
                  RSI训练完成后，优化参数和校准系数将自动应用到所有后续压力测试中。压力测试引擎在估值时会加载最新的RSI参数，实现精度持续提升。
                </p>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ============ 子组件 ============

function MetricCard({
  title,
  value,
  icon: Icon,
  color,
  bgColor,
  subtitle,
}: {
  title: string;
  value: string;
  icon: typeof TrendingDown;
  color: string;
  bgColor: string;
  subtitle?: string;
}) {
  return (
    <div className="card p-4 hover:border-line-soft transition-all duration-200">
      <div className="flex items-start justify-between mb-3">
        <span className="text-xs text-t3">{title}</span>
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ backgroundColor: bgColor }}
        >
          <Icon className="w-4 h-4" style={{ color }} />
        </div>
      </div>
      <div className="num text-xl font-bold text-t1 leading-tight">{value}</div>
      {subtitle && <p className="text-[10px] text-t4 mt-1">{subtitle}</p>}
    </div>
  );
}

function FlowStep({
  step,
  title,
  desc,
  icon: Icon,
  color,
}: {
  step: string;
  title: string;
  desc: string;
  icon: typeof Target;
  color: string;
}) {
  return (
    <div className="bg-elevated rounded-lg p-4 border border-line/50">
      <div className="flex items-center gap-2 mb-3">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ backgroundColor: `${color}15` }}
        >
          <Icon className="w-4 h-4" style={{ color }} />
        </div>
        <div>
          <span className="text-[10px] text-t4 font-mono">{step}</span>
          <h5 className="text-sm font-medium text-t1 leading-tight">{title}</h5>
        </div>
      </div>
      <p className="text-xs text-t3 leading-relaxed">{desc}</p>
    </div>
  );
}

// ============ MAE趋势图 (SVG) ============

function MAEChart({
  data,
}: {
  data: Array<{ epoch: number; mae: number; mape: number; r2: number }>;
}) {
  const width = 800;
  const height = 200;
  const padding = { top: 20, right: 40, bottom: 30, left: 60 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const values = data.map((d) => d.mae).filter((v) => v != null) as number[];
  if (values.length === 0) return null;

  const maxVal = Math.max(...values);
  const minVal = Math.min(...values);
  const range = maxVal - minVal || 1;

  const xStep = data.length > 1 ? chartW / (data.length - 1) : 0;

  // 归一化Y坐标
  const getY = (val: number) => padding.top + chartH - ((val - minVal) / range) * chartH;
  const getX = (idx: number) => padding.left + idx * xStep;

  // 生成路径
  const linePath = data
    .map((d, i) => `${i === 0 ? 'M' : 'L'} ${getX(i)} ${getY(d.mae)}`)
    .join(' ');

  // 生成面积路径
  const areaPath =
    `${linePath} L ${getX(data.length - 1)} ${padding.top + chartH} ` +
    `L ${getX(0)} ${padding.top + chartH} Z`;

  // Y轴刻度
  const yTicks = 4;
  const tickValues = Array.from({ length: yTicks + 1 }, (_, i) => minVal + (range * i) / yTicks);

  return (
    <div className="overflow-x-auto">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full"
        style={{ minWidth: '500px' }}
      >
        {/* 背景网格 */}
        {tickValues.map((tv, i) => {
          const y = getY(tv);
          return (
            <g key={i}>
              <line
                x1={padding.left}
                y1={y}
                x2={width - padding.right}
                y2={y}
                stroke="#1a2535"
                strokeWidth="1"
                strokeDasharray="2,4"
              />
              <text
                x={padding.left - 8}
                y={y + 4}
                fill="#5d6b7e"
                fontSize="10"
                textAnchor="end"
                fontFamily="JetBrains Mono"
              >
                {tv.toFixed(4)}
              </text>
            </g>
          );
        })}

        {/* 面积渐变 */}
        <defs>
          <linearGradient id="maeGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#f0b90b" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#f0b90b" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={areaPath} fill="url(#maeGradient)" />

        {/* 折线 */}
        <path
          d={linePath}
          fill="none"
          stroke="#f0b90b"
          strokeWidth="2"
          strokeLinejoin="round"
          strokeLinecap="round"
        />

        {/* 数据点 */}
        {data.map((d, i) => {
          const x = getX(i);
          const y = getY(d.mae);
          return (
            <g key={i}>
              <circle cx={x} cy={y} r="4" fill="#0d1420" stroke="#f0b90b" strokeWidth="2" />
              <text
                x={x}
                y={padding.top + chartH + 20}
                fill="#5d6b7e"
                fontSize="10"
                textAnchor="middle"
                fontFamily="JetBrains Mono"
              >
                {d.epoch}
              </text>
            </g>
          );
        })}

        {/* 标签 */}
        <text
          x={padding.left}
          y={padding.top - 6}
          fill="#5d6b7e"
          fontSize="10"
          fontFamily="Noto Sans SC"
        >
          MAE (平均绝对误差)
        </text>
        <text
          x={width - padding.right}
          y={padding.top + chartH + 20}
          fill="#5d6b7e"
          fontSize="10"
          textAnchor="end"
          fontFamily="Noto Sans SC"
        >
          迭代轮次 →
        </text>
      </svg>
    </div>
  );
}
