import { MessageSquare, Wallet, BarChart3, TrendingUp, Activity, BrainCircuit } from 'lucide-react';
import type { ViewType } from '../types';

interface SidebarProps {
  activeView: ViewType;
  onViewChange: (view: ViewType) => void;
}

const navItems: { id: ViewType; label: string; icon: typeof MessageSquare; desc: string }[] = [
  { id: 'chat', label: 'AI压力交互', icon: MessageSquare, desc: '智能场景解析' },
  { id: 'positions', label: '持仓管理', icon: Wallet, desc: '期权持仓总览' },
  { id: 'stress-test', label: '压力测试结果', icon: BarChart3, desc: 'P&L分析报告' },
  { id: 'market', label: '市场数据', icon: TrendingUp, desc: '实时风险因子' },
  { id: 'rsi', label: 'RSI自我进化', icon: BrainCircuit, desc: '计量引擎递归提升' },
];

export default function Sidebar({ activeView, onViewChange }: SidebarProps) {
  return (
    <aside className="w-60 bg-surface border-r border-line flex flex-col flex-shrink-0">
      {/* Logo 区域 */}
      <div className="h-16 flex items-center px-5 border-b border-line">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-gold to-gold-dark flex items-center justify-center shadow-glow-gold">
            <Activity className="w-5 h-5 text-base" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-t1 leading-tight tracking-wide">场外衍生品</h1>
            <p className="text-[11px] text-t3 leading-tight">智能压力测试平台</p>
          </div>
        </div>
      </div>

      {/* 导航菜单 */}
      <nav className="flex-1 p-3 space-y-1">
        <div className="px-3 py-2 text-[10px] uppercase tracking-widest text-t4 font-medium">
          功能导航
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeView === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onViewChange(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-sm transition-all duration-200 group ${
                isActive
                  ? 'bg-active text-gold border border-gold/30'
                  : 'text-t2 hover:bg-hover hover:text-t1 border border-transparent'
              }`}
            >
              <Icon
                className={`w-4 h-4 flex-shrink-0 ${
                  isActive ? 'text-gold' : 'text-t3 group-hover:text-t2'
                }`}
              />
              <div className="flex-1 text-left">
                <div className="font-medium leading-tight">{item.label}</div>
                <div
                  className={`text-[10px] leading-tight mt-0.5 ${
                    isActive ? 'text-gold/60' : 'text-t4'
                  }`}
                >
                  {item.desc}
                </div>
              </div>
            </button>
          );
        })}
      </nav>

      {/* 底部状态栏 */}
      <div className="p-3 border-t border-line">
        <div className="flex items-center gap-2 px-3 py-2 rounded-md bg-elevated">
          <span className="w-2 h-2 rounded-full bg-success animate-pulse-slow" />
          <span className="text-xs text-t3">系统运行中</span>
          <span className="ml-auto text-[10px] text-t4 num">v1.0.0</span>
        </div>
      </div>
    </aside>
  );
}
