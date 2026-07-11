@echo off
REM RSI每日午夜自动优化任务
REM 由Windows任务计划程序在每日0:00调用

cd /d "C:\Users\swok2\Desktop\场外衍生品智能压力测试"
python rsi_scheduler.py
