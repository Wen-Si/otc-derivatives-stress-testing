// ============================================
// 场外衍生品智能压力测试平台 - 类型定义
// ============================================

// 风险因子类型
export type FactorType = 'price' | 'volatility' | 'risk_free_rate';

// 冲击类型
export type ShockType = 'relative' | 'absolute';

// 期权类型(19种)
export type OptionType =
  | 'european' | 'american' | 'asian' | 'barrier' | 'lookback'
  | 'binary' | 'chooser' | 'compound' | 'forward_start' | 'power'
  | 'exchange' | 'cliquet' | 'shout' | 'double_barrier' | 'range'
  | 'quanto' | 'rainbow' | 'spread' | 'barrier_lookback';

// 认购/认沽
export type CallPut = 'call' | 'put';

// 持仓方向
export type PositionDirection = 'long' | 'short';

// 风险因子冲击
export interface Shock {
  factor_name: string;
  factor_type: FactorType;
  shock_type: ShockType;
  shock_value: number;
  description: string;
}

// 压力场景
export interface Scenario {
  name: string;
  description: string;
  shocks: Shock[];
}

// Chat 接口响应
export interface ChatResponse {
  reply: string;
  scenario: Scenario;
}

// 持仓
export interface Position {
  id: number;
  name: string;
  option_type: OptionType;
  call_put: CallPut;
  underlying_name: string;
  strike: number;
  maturity_date: string;
  quantity: number;
  position_direction: PositionDirection;
  notional: number;
  current_value: number;
  entry_price: number;
}

// 压力测试结果 - 单条持仓
export interface StressTestResultItem {
  position_id: number;
  position_name: string;
  original_value: number;
  stressed_value: number;
  pnl_change: number;
  pnl_pct: number;
}

// 压力测试结果 - 完整响应
export interface StressTestResponse {
  scenario_id: number;
  scenario_name: string;
  total_pnl: number;
  total_pnl_pct: number;
  shocks: Shock[];
  results: StressTestResultItem[];
}

// 风险因子（市场数据）
export interface RiskFactor {
  index_price: number;
  volatility: number;
  risk_free_rate: number;
  [key: string]: number;
}

// 历史场景列表项
export interface ScenarioListItem {
  id: number;
  name: string;
  description: string;
}

// 历史压力测试场景
export interface HistoricalScenario {
  id: string;
  name: string;
  description: string;
  event_type: string;
  severity: string;
  start_date: string;
  end_date: string;
}

// RSI 迭代轮次记录
export interface RSIEpoch {
  id: number;
  epoch: number;
  name: string;
  description: string;
  mae: number;
  rmse: number;
  mape: number;
  r_squared: number;
  max_error: number;
  model_params: Record<string, number> | null;
  calibration_factors: Record<string, number> | null;
  converged: boolean;
  improvement_pct: number;
  n_samples: number;
  created_at: string;
}

// RSI 状态概览
export interface RSIStatus {
  total_epochs: number;
  converged_count: number;
  is_active: boolean;
  latest_epoch: number | null;
  latest_mae: number | null;
  latest_mape: number | null;
  latest_r_squared: number | null;
  latest_converged: boolean;
  latest_improvement_pct: number | null;
  current_model_params: Record<string, number>;
  current_calibration: Record<string, number>;
  is_using_default: boolean;
}

// RSI 运行结果
export interface RSIRunResult {
  success: boolean;
  n_iterations: number;
  start_epoch: number;
  converged: boolean;
  initial_metrics: {
    mae: number;
    rmse: number;
    mape: number;
    r_squared: number;
    max_error: number;
  };
  final_metrics: {
    mae: number;
    rmse: number;
    mape: number;
    r_squared: number;
    max_error: number;
  };
  total_improvement_pct: number;
  final_model_params: Record<string, number>;
  final_calibration_factors: Record<string, number>;
  iterations: Array<{
    epoch: number;
    metrics: {
      mae: number;
      rmse: number;
      mape: number;
      r_squared: number;
      max_error: number;
    };
    model_params: Record<string, number>;
    calibration_factors: Record<string, number>;
    improvement_pct: number;
    converged: boolean;
    n_samples: number;
  }>;
  n_samples: number;
}

// 视图类型
export type ViewType = 'chat' | 'positions' | 'stress-test' | 'market' | 'rsi';

// Greeks(完整版14个)
export interface Greeks {
  // 一阶
  delta: number;
  vega: number;
  theta: number;
  rho: number;
  // 二阶
  gamma: number;
  vanna: number;
  volga: number;
  charm: number;
  veta: number;
  color: number;
  zomma: number;
  // 三阶
  speed: number;
  ultima: number;
  // 其他
  lambda: number;
}

// 期权类型信息
export interface OptionTypeInfo {
  type: string;
  name: string;
}

// 定价结果
export interface PricingResult {
  success: boolean;
  option_type: string;
  option_name: string;
  price: number;
  inputs: Record<string, number | string>;
}

// Greeks计算结果
export interface GreeksResult {
  success: boolean;
  option_type: string;
  option_name: string;
  greeks: Greeks;
  inputs: Record<string, number | string>;
}
