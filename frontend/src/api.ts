// ============================================
// API 调用封装
// 后端地址: http://localhost:8000
// 通过 Vite 代理转发 /api 请求
// GitHub Pages部署时自动检测并使用可配置后端地址
// ============================================

import axios from 'axios';
import type {
  ChatResponse,
  Position,
  StressTestResponse,
  RiskFactor,
  Scenario,
  ScenarioListItem,
  RSIRunResult,
  RSIEpoch,
  RSIStatus,
} from './types';

// 检测是否在GitHub Pages上运行
const isGitHubPages = window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1';

// 从localStorage读取用户配置的后端地址,默认localhost:8000
const getBackendURL = (): string => {
  if (isGitHubPages) {
    const saved = localStorage.getItem('backend_url');
    if (saved) return saved;
    return '';  // 空字符串表示未配置后端
  }
  return '';  // 本地开发使用Vite代理
};

const backendURL = getBackendURL();
const baseURL = backendURL ? `${backendURL}/api` : '/api';

const api = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 导出配置函数供UI使用
export function setBackendURL(url: string) {
  if (url) {
    localStorage.setItem('backend_url', url);
  } else {
    localStorage.removeItem('backend_url');
  }
  window.location.reload();
}

export function getBackendStatus() {
  return {
    isGitHubPages,
    backendURL: backendURL || '(默认/Vite代理)',
    hasBackend: !isGitHubPages || !!backendURL,
  };
}

export { isGitHubPages };

// POST /api/chat - 发送自然语言消息，获取AI解析的压力场景
export async function sendChatMessage(message: string): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>('/chat', { message }, { timeout: 60000 });
  return data;
}

// GET /api/positions - 获取持仓列表（含当前估值）
export async function getPositions(): Promise<Position[]> {
  const { data } = await api.get<Position[]>('/positions');
  return data;
}

// POST /api/stress-test/run - 执行压力测试
export async function runStressTest(scenario: Scenario): Promise<StressTestResponse> {
  const { data } = await api.post<StressTestResponse>('/stress-test/run', { scenario }, { timeout: 120000 });
  return data;
}

// GET /api/risk-factors - 获取当前风险因子（市场数据）
export async function getRiskFactors(): Promise<RiskFactor> {
  const { data } = await api.get<RiskFactor>('/risk-factors');
  return data;
}

// GET /api/stress-test/scenarios - 获取历史场景列表
export async function getScenarios(): Promise<ScenarioListItem[]> {
  const { data } = await api.get<ScenarioListItem[]>('/stress-test/scenarios');
  return data;
}

// GET /api/stress-test/scenarios/{id} - 获取场景详情
export async function getScenarioDetail(id: number): Promise<Scenario> {
  const { data } = await api.get<Scenario>(`/stress-test/scenarios/${id}`);
  return data;
}

// ============ 历史压力测试场景接口 ============

// GET /api/historical-scenarios - 获取历史场景列表
export async function getHistoricalScenarios() {
  const { data } = await api.get('/historical-scenarios');
  return data;
}

// GET /api/historical-scenarios/{id} - 获取历史场景详情(含Tushare数据)
export async function getHistoricalScenarioDetail(scenarioId: string) {
  const { data } = await api.get(`/historical-scenarios/${scenarioId}`);
  return data;
}

// POST /api/historical-scenarios/{id}/run - 执行历史场景压力测试
export async function runHistoricalScenario(scenarioId: string) {
  const { data } = await api.post(`/historical-scenarios/${scenarioId}/run`, {}, { timeout: 120000 });
  return data;
}

// ============ RSI(递归自我提升)接口 ============

// POST /api/rsi/run - 触发RSI递归自我提升
export async function runRSI(maxIterations: number = 3): Promise<RSIRunResult> {
  const { data } = await api.post<RSIRunResult>(`/rsi/run?max_iterations=${maxIterations}`, {}, { timeout: 300000 });
  return data;
}

// GET /api/rsi/status - 获取RSI引擎状态概览
export async function getRSIStatus(): Promise<RSIStatus> {
  const { data } = await api.get<RSIStatus>('/rsi/status');
  return data;
}

// GET /api/rsi/history - 获取RSI所有迭代历史
export async function getRSIHistory(): Promise<{ success: boolean; epochs: RSIEpoch[] }> {
  const { data } = await api.get('/rsi/history');
  return data;
}

// GET /api/rsi/latest - 获取最新RSI结果
export async function getRSILatest() {
  const { data } = await api.get('/rsi/latest');
  return data;
}

export default api;
