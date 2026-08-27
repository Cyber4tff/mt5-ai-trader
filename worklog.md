---
Task ID: 1
Agent: Main Agent
Task: Fix multiple UI issues - launch animation, theme toggle, Error 10, MT5 confirmation, account balance display

Work Log:
- Created ThemeProvider in src/components/providers.tsx wrapping next-themes
- Updated src/app/layout.tsx to include ThemeProvider
- Created launch animation component (src/components/trading/launch-screen.tsx) with logo animation, loading bar
- Added LiveConnectionState to trading-store.ts with mt5Confirmed, manualBalance, manualEquity
- Added confirmMT5Connection and unconfirmMT5Connection actions to store
- Updated connection-panel.tsx with MT5 confirmation flow, balance display, theme-aware classes
- Updated web-terminal-panel.tsx with Error 10 troubleshooting guide, connection prompt overlay
- Updated auto-trade-panel.tsx to require mt5Confirmed in live mode before enabling scanning
- Created LiveBalanceCard component in page.tsx for displaying/updating balance in live mode
- Converted all components from hardcoded dark (zinc-950, zinc-900, etc.) to theme-aware classes (bg-card, bg-background, text-foreground, text-muted-foreground, border-border)
- Fixed header.tsx theme toggle button to work with ThemeProvider
- Updated all trading components: ai-status-panel, scanner-panel, scan-log, account-cards, risk-panel, positions-table
- Fixed JSX comment parsing error in web-terminal-panel.tsx (missing closing })

Stage Summary:
- Theme toggle now works (dark/light mode switching)
- Launch animation shows on page load (2.5s duration)
- Error 10 gets a troubleshooting guide panel with best practices
- MT5 must be confirmed connected before auto-trading enables in live mode
- Account balance can be manually entered and displayed in live mode
- All components properly support light and dark themes
