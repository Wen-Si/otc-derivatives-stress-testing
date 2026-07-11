import { useState } from 'react';
import Sidebar from './Sidebar';
import ChatPanel from './ChatPanel';
import PositionsTable from './PositionsTable';
import StressTestResults from './StressTestResults';
import MarketData from './MarketData';
import RSIEngine from './RSIEngine';
import type { ViewType, StressTestResponse } from '../types';
import { isGitHubPages, getBackendStatus, setBackendURL } from '../api';

const viewTitles: Record<ViewType, string> = {
  chat: 'AI 智能压力交互',
  positions: '持仓管理',
  'stress-test': '压力测试结果',
  market: '市场数据',
  rsi: 'RSI 递归自我提升',
};

const viewSubtitles: Record<ViewType, string> = {
  chat: '通过自然语言描述压力场景，AI 自动解析风险因子冲击',
  positions: '场外期权持仓总览及实时估值',
  'stress-test': '压力测试下的持仓估值变化与 P&L 分析',
  market: '当前市场环境下的核心风险因子数据',
  rsi: '计量引擎自我评估、参数优化、知识积累的递归进化',
};

export default function Dashboard() {
  const [activeView, setActiveView] = useState<ViewType>('chat');
  const [stressTestResult, setStressTestResult] = useState<StressTestResponse | null>(null);
  const [showBackendConfig, setShowBackendConfig] = useState(false);
  const [backendInput, setBackendInput] = useState('');

  const handleStressTestComplete = (result: StressTestResponse) => {
    setStressTestResult(result);
    setActiveView('stress-test');
  };

  const now = new Date();
  const dateStr = now.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
  const timeStr = now.toLocaleTimeString('zh-CN', { hour12: false });

  const backendStatus = getBackendStatus();

  return (
    <div className="flex h-screen overflow-hidden bg-base">
      <Sidebar activeView={activeView} onViewChange={setActiveView} />
      <main className="flex-1 overflow-hidden flex flex-col">
        {/* 顶部栏 */}
        <header className="h-14 border-b border-line bg-surface flex items-center px-6 flex-shrink-0">
          <div>
            <h2 className="text-base font-semibold text-t1 leading-tight">
              {viewTitles[activeView]}
            </h2>
            <p className="text-[11px] text-t3 leading-tight mt-0.5">
              {viewSubtitles[activeView]}
            </p>
          </div>
          <div className="ml-auto flex items-center gap-4 text-xs text-t3">
            {isGitHubPages && (
              <button
                onClick={() => setShowBackendConfig(!showBackendConfig)}
                className="flex items-center gap-2 px-3 py-1 rounded-md border border-line hover:border-primary transition-colors"
                title="配置后端地址"
              >
                <span className={`w-1.5 h-1.5 rounded-full ${backendStatus.hasBackend ? 'bg-success' : 'bg-danger'}`} />
                <span>{backendStatus.hasBackend ? '后端已连接' : '后端未连接'}</span>
              </button>
            )}
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse-slow" />
              <span>实时数据</span>
            </div>
            <span className="w-px h-4 bg-line" />
            <span className="num">{dateStr}</span>
            <span className="num text-gold">{timeStr}</span>
          </div>
        </header>

        {/* 后端配置面板(GitHub Pages模式) */}
        {isGitHubPages && showBackendConfig && (
          <div className="border-b border-line bg-surface px-6 py-4 flex items-center gap-4">
            <span className="text-sm text-t2 font-medium">后端地址:</span>
            <input
              type="text"
              value={backendInput}
              onChange={(e) => setBackendInput(e.target.value)}
              placeholder="http://your-server:8000"
              className="flex-1 max-w-md px-3 py-1.5 text-sm border border-line rounded-md bg-base text-t1 focus:outline-none focus:border-primary"
            />
            <button
              onClick={() => { if (backendInput) setBackendURL(backendInput); }}
              className="px-4 py-1.5 text-sm bg-primary text-white rounded-md hover:opacity-90"
            >
              连接
            </button>
            {backendStatus.backendURL !== '(默认/Vite代理)' && (
              <button
                onClick={() => setBackendURL('')}
                className="px-4 py-1.5 text-sm border border-line rounded-md hover:border-danger text-t3"
              >
                清除
              </button>
            )}
            <span className="text-xs text-t3">
              提示: 输入运行后端服务的服务器地址(含http://和端口)
            </span>
          </div>
        )}

        {/* GitHub Pages提示栏 */}
        {isGitHubPages && !backendStatus.hasBackend && (
          <div className="bg-warning/10 border-b border-warning/30 px-6 py-3">
            <p className="text-sm text-warning">
              <strong>在线演示模式:</strong> 后端服务未连接,部分功能(压力测试/AI对话/RSI)不可用。
              点击右上角"后端未连接"按钮配置后端地址,或在本地运行完整平台。
            </p>
          </div>
        )}

        {/* 内容区 */}
        <div className="flex-1 overflow-auto bg-gradient-surface">
          {activeView === 'chat' && (
            <ChatPanel onStressTestComplete={handleStressTestComplete} />
          )}
          {activeView === 'positions' && <PositionsTable />}
          {activeView === 'stress-test' && <StressTestResults result={stressTestResult} />}
          {activeView === 'market' && <MarketData />}
          {activeView === 'rsi' && <RSIEngine />}
        </div>
      </main>
    </div>
  );
}
