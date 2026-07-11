import React, { useState, useRef, useEffect } from 'react';
import { sendChatMessage, runStressTest } from '../api';
import type { Scenario, Shock, StressTestResponse } from '../types';
import {
  Send,
  Sparkles,
  Play,
  Loader2,
  TrendingDown,
  Activity,
  Percent,
  AlertTriangle,
  Zap,
  ShieldAlert,
} from 'lucide-react';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  scenario?: Scenario;
}

interface ChatPanelProps {
  onStressTestComplete: (result: StressTestResponse) => void;
}

// 格式化冲击值
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

// 获取冲击图标
function getShockIcon(factorType: string) {
  switch (factorType) {
    case 'price':
      return TrendingDown;
    case 'volatility':
      return Activity;
    case 'risk_free_rate':
      return Percent;
    default:
      return AlertTriangle;
  }
}

// 获取冲击颜色
function getShockColor(factorType: string, value: number): string {
  if (factorType === 'price') {
    return value < 0 ? '#ff4757' : '#00c853';
  }
  return '#00d4ff';
}

// 场景卡片
function ScenarioCard({ scenario }: { scenario: Scenario }) {
  return (
    <div className="mt-3 card-elevated p-4 border-gold/20">
      <div className="flex items-center gap-2 mb-3">
        <Zap className="w-4 h-4 text-gold" />
        <span className="text-sm font-medium text-gold">AI 解析场景</span>
      </div>
      <div className="mb-3">
        <h4 className="text-sm font-semibold text-t1 mb-1">{scenario.name}</h4>
        <p className="text-xs text-t3">{scenario.description}</p>
      </div>
      <div className="space-y-2">
        {scenario.shocks.map((shock, idx) => {
          const Icon = getShockIcon(shock.factor_type);
          const color = getShockColor(shock.factor_type, shock.shock_value);
          return (
            <div key={idx} className="flex items-center gap-3 p-2.5 rounded-md bg-base/50">
              <div
                className="w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0"
                style={{ backgroundColor: `${color}15` }}
              >
                <Icon className="w-3.5 h-3.5" style={{ color }} />
              </div>
              <div className="flex-1 min-w-0">
                <span className="text-xs text-t2">{shock.factor_name}</span>
                <span className="text-[10px] text-t4 ml-2">{shock.description}</span>
              </div>
              <span className="num text-sm font-semibold flex-shrink-0" style={{ color }}>
                {formatShockValue(shock)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const quickExamples = [
  '市场突然下跌10%，波动率上升5%，国债收益率上升30bp',
  '极端黑天鹅事件：指数下跌20%，波动率翻倍',
  '温和回调场景：指数下跌5%，波动率上升2%',
];

export default function ChatPanel({ onStressTestComplete }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content:
        '您好，我是智能压力测试助手。请用自然语言描述您想测试的压力场景，例如"市场突然下跌10%，波动率上升5%"。我将为您解析风险因子冲击并执行压力测试。',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [currentScenario, setCurrentScenario] = useState<Scenario | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    const message = input.trim();
    if (!message || loading) return;

    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: message }]);
    setLoading(true);
    setCurrentScenario(null);

    try {
      const response = await sendChatMessage(message);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: response.reply, scenario: response.scenario },
      ]);
      setCurrentScenario(response.scenario);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content:
            '抱歉，解析请求时出现错误。请确认后端服务 (http://localhost:8000) 已启动并正常运行。',
        },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleRunStressTest = async () => {
    if (!currentScenario || testing) return;
    setTesting(true);
    try {
      const result = await runStressTest(currentScenario);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `压力测试已完成。在"${result.scenario_name}"场景下，组合总盈亏为 ${result.total_pnl >= 0 ? '+' : ''}${result.total_pnl.toLocaleString()} 元（${(result.total_pnl_pct * 100).toFixed(2)}%）。您可在"压力测试结果"页面查看详细分析。`,
        },
      ]);
      onStressTestComplete(result);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: '压力测试执行失败，请确认后端服务正常运行。',
        },
      ]);
    } finally {
      setTesting(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleExample = (example: string) => {
    setInput(example);
    inputRef.current?.focus();
  };

  return (
    <div className="flex flex-col h-full">
      {/* 消息列表 */}
      <div className="flex-1 overflow-auto px-6 py-4">
        <div className="max-w-4xl mx-auto space-y-4">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`}
            >
              <div className={`max-w-3xl ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                {/* 消息头 */}
                {msg.role === 'assistant' && (
                  <div className="flex items-center gap-2 mb-1.5 ml-1">
                    <div className="w-6 h-6 rounded-md bg-gradient-to-br from-gold to-gold-dark flex items-center justify-center">
                      <Sparkles className="w-3 h-3 text-base" />
                    </div>
                    <span className="text-xs text-t3 font-medium">AI 助手</span>
                  </div>
                )}
                {/* 消息气泡 */}
                <div
                  className={`rounded-lg px-4 py-3 text-sm leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-active border border-gold/30 text-t1'
                      : 'card text-t2'
                  }`}
                >
                  {msg.content}
                  {msg.scenario && <ScenarioCard scenario={msg.scenario} />}
                </div>
              </div>
            </div>
          ))}

          {/* 加载指示器 */}
          {loading && (
            <div className="flex justify-start animate-fade-in">
              <div className="flex items-center gap-2 mb-1.5 ml-1">
                <div className="w-6 h-6 rounded-md bg-gradient-to-br from-gold to-gold-dark flex items-center justify-center">
                  <Sparkles className="w-3 h-3 text-base" />
                </div>
                <span className="text-xs text-t3 font-medium">AI 助手</span>
              </div>
              <div className="card px-4 py-3 flex items-center gap-2">
                <div className="flex gap-1">
                  <span
                    className="w-2 h-2 rounded-full bg-gold animate-bounce"
                    style={{ animationDelay: '0ms' }}
                  />
                  <span
                    className="w-2 h-2 rounded-full bg-gold animate-bounce"
                    style={{ animationDelay: '150ms' }}
                  />
                  <span
                    className="w-2 h-2 rounded-full bg-gold animate-bounce"
                    style={{ animationDelay: '300ms' }}
                  />
                </div>
                <span className="text-xs text-t3 ml-1">正在解析场景...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* 执行压力测试按钮 */}
      {currentScenario && !loading && (
        <div className="px-6 pb-2 max-w-4xl mx-auto w-full animate-fade-in">
          <button
            onClick={handleRunStressTest}
            disabled={testing}
            className="btn-primary w-full py-3 text-sm shadow-glow-gold"
          >
            {testing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                正在执行压力测试...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                执行压力测试
              </>
            )}
          </button>
        </div>
      )}

      {/* 快速示例 */}
      {messages.length <= 1 && !loading && (
        <div className="px-6 pb-2 max-w-4xl mx-auto w-full animate-fade-in">
          <div className="flex items-center gap-2 mb-2">
            <ShieldAlert className="w-3.5 h-3.5 text-t3" />
            <span className="text-xs text-t3">快速场景示例</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {quickExamples.map((ex, idx) => (
              <button
                key={idx}
                onClick={() => handleExample(ex)}
                className="card-elevated px-3 py-1.5 text-xs text-t2 hover:text-gold hover:border-gold/30 transition-all"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 输入区域 */}
      <div className="border-t border-line bg-surface p-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-end gap-3">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={1}
                placeholder="描述您的压力测试场景，例如：市场下跌10%，波动率上升5%..."
                className="w-full bg-elevated border border-line rounded-lg px-4 py-3 text-sm text-t1 placeholder-t4 resize-none focus:border-gold/40 transition-colors"
                style={{ minHeight: '44px', maxHeight: '120px' }}
              />
            </div>
            <button
              onClick={handleSend}
              disabled={!input.trim() || loading}
              className="btn-primary py-3 px-5"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  发送
                </>
              )}
            </button>
          </div>
          <p className="text-[10px] text-t4 mt-2 text-center">
            按 Enter 发送，Shift + Enter 换行
          </p>
        </div>
      </div>
    </div>
  );
}
