#!/bin/bash
echo "Starting Runbook..."
echo ""
echo "1. Starting Backend (port 8000)..."
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

echo ""
echo "2. Starting Frontend (port 5174)..."
cd frontend && npm run dev &
FRONTEND_PID=$!
cd ..
echo "   Frontend PID: $FRONTEND_PID"

echo ""
echo "3. Starting Discord Bot..."
python -m discord_bot.bot &
BOT_PID=$!
echo "   Bot PID: $BOT_PID"

echo ""
echo "==================================="
echo "Runbook is running:"
echo "  Dashboard: http://localhost:5174"
echo "  Backend:   http://localhost:8000"
echo "  Discord:   Bot connected"
echo "==================================="
echo ""
echo "Press Ctrl+C to stop all services."

trap "kill $BACKEND_PID $FRONTEND_PID $BOT_PID 2>/dev/null" EXIT
wait
