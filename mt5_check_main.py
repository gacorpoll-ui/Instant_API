import sys, os, time, math
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', buffering=1)
sys.path.insert(0, r'D:\master-trader\xauusd_bot')
import MetaTrader5 as mt5, pandas as pd

SYMBOL = 'XAUUSDc'
LOGIN = 160035155
PASSWORD = '3_TIGA_three'
SERVER = 'Exness-MT5Real20'
TERM_PATH = r'C:\Program Files\MetaTrader 5\terminal64.exe'

for attempt in range(3):
    try: mt5.shutdown()
    except: pass
    time.sleep(1)
    if mt5.initialize(path=TERM_PATH, login=LOGIN, password=PASSWORD, server=SERVER): break
    if mt5.initialize(path=TERM_PATH): break
    if mt5.initialize(): break

mt5.symbol_select(SYMBOL, True)
time.sleep(0.5)

acct = mt5.account_info()
if not acct:
    print("MT5 FAILED"); sys.exit(1)

balance = acct.balance
print(f'Account: {acct.login} @ {acct.server} | Balance: ${balance:.2f} | Equity: ${acct.equity:.2f}')

tick = mt5.symbol_info_tick(SYMBOL)
if tick:
    print(f'Symbol: {SYMBOL} | Price: {tick.bid:.3f}/{tick.ask:.3f}')

# Verify contract spec for pip value calculation
sym_info = mt5.symbol_info(SYMBOL)
if sym_info:
    contract_size = sym_info.trade_contract_size
    point = sym_info.point
    pip_value = contract_size * point  # $ per 1 pip for 0.01 lot
    print(f'Contract: {contract_size} | Point: {point} | Pip Value (0.01 lot): ${pip_value:.2f}')
else:
    print("WARNING: Could not retrieve symbol info")
    pip_value = 10  # Default fallback

# TF analysis
tf_data = {}
atr_h1 = 0
for tf_name, tf_const in [('M5',mt5.TIMEFRAME_M5),('M15',mt5.TIMEFRAME_M15),('H1',mt5.TIMEFRAME_H1),('H4',mt5.TIMEFRAME_H4)]:
    rates = mt5.copy_rates_from_pos(SYMBOL, tf_const, 0, 500)
    if rates is None or len(rates) < 250: continue
    df = pd.DataFrame(rates)
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    trs = []
    for i in range(1, min(16, len(df))):
        tr = max(df.iloc[i]['high']-df.iloc[i]['low'], abs(df.iloc[i]['high']-df.iloc[i-1]['close']), abs(df.iloc[i]['low']-df.iloc[i-1]['close']))
        trs.append(tr)
    atr = sum(trs[-13:])/13 if len(trs)>=13 else 0
    price = df.iloc[-1]['close']
    vs200 = 'ABOVE' if price > df.iloc[-1]['ema200'] else 'BELOW'
    slope = 'UP' if df.iloc[-1]['ema20'] > df.iloc[-5]['ema20'] else 'DOWN'
    trend = 'BULLISH' if (vs200 == 'ABOVE' and slope == 'UP') else 'BEARISH' if (vs200 == 'BELOW' and slope == 'DOWN') else 'RANGING'
    tf_data[tf_name] = {'trend': trend, 'atr': atr, 'slope': slope, 'price': price}
    print(f'  {tf_name}: Price={price:.2f} vs200={vs200} ATR={atr:.2f} EMA20_slope={slope} Trend={trend}')
    if tf_name == 'H1':
        atr_h1 = atr

# Position management
pos = mt5.positions_get(symbol=SYMBOL)
if pos:
    for p in pos:
        pt = 'BUY' if p.type == mt5.ORDER_TYPE_BUY else 'SELL'
        print(f'  POS: #{p.ticket} {pt} {p.volume}lot Entry:{p.price_open:.2f} SL:{p.sl} TP:{p.tp} P&L:${p.profit:.2f}')
        # Trail SL to breakeven when profit > $10
        if p.profit > 10:
            new_sl = p.price_open + 0.5 if pt == 'BUY' else p.price_open - 0.5
            if (pt == 'BUY' and new_sl > p.sl) or (pt == 'SELL' and new_sl < p.sl):
                req = {'action': mt5.TRADE_ACTION_SLTP, 'symbol': p.symbol, 'sl': round(new_sl, 3), 'tp': p.tp, 'position': p.ticket}
                res = mt5.order_send(req)
                if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f'  SL trailed to breakeven: {p.sl:.3f} -> {new_sl:.3f}')
else:
    print('  No open positions')
    # RECOVERY RULES:
    # 1. ALL 3 TF must align (M15+H1+H4)
    # 2. ATR H1 < 20
    # 3. Lot = 2% risk (max $12.44 from $622)
    # 4. SL = 30 pts (wide enough for ATR 19)
    # 5. TP = 60 pts (RR 1:2)

    trends = {k: v['trend'] for k, v in tf_data.items()}
    all_bearish = all(t == 'BEARISH' for t in trends.values())
    all_bullish = all(t == 'BULLISH' for t in trends.values())

    if (all_bearish or all_bullish) and atr_h1 < 20 and tick:
        direction = 'SELL' if all_bearish else 'BUY'
        entry = tick.bid if direction == 'SELL' else tick.ask
        sl_pts = 30.0  # WIDE SL
        tp_pts = sl_pts * 2.0  # RR 1:2
        
        if direction == 'SELL':
            sl = entry + sl_pts
            tp = entry - tp_pts
        else:
            sl = entry - sl_pts
            tp = entry + tp_pts
        
        # Lot = 2% risk: risk = balance * 0.02, lot = risk / (sl_pts * pip_value)
        # pip_value = contract_size * point = $ per 1 pip for 0.01 lot
        # Dynamic cap: max_lot = balance / 10000 (proportional growth)
        risk = balance * 0.02  # 2% = $12.44
        lot = risk / (sl_pts * pip_value)  # Accurate based on Exness contract spec
        max_lot = round(balance / 10000, 2)  # Dynamic max: scales with balance
        lot = max(0.01, min(max_lot, round(lot / 0.01) * 0.01))
        max_loss = sl_pts * lot * pip_value
        
        print(f'\n  >>> RECOVERY ENTRY: {direction}')
        print(f'  ALL TF {direction.upper()} | ATR H1: {atr_h1:.2f} < 20')
        print(f'  Entry: {entry:.3f} | SL: {sl:.3f} ({sl_pts:.0f} pts) | TP: {tp:.3f}')
        print(f'  Lot: {lot:.2f} | Max Loss: ${max_loss:.2f} ({max_loss/balance*100:.1f}%) | Risk: 2%')
        
        order_type = mt5.ORDER_TYPE_SELL if direction == 'SELL' else mt5.ORDER_TYPE_BUY
        price = tick.bid if direction == 'SELL' else tick.ask
        request = {
            "action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL, "volume": lot,
            "type": order_type, "price": price, "sl": round(sl, 3), "tp": round(tp, 3),
            "deviation": 20, "magic": 202606, "comment": "Recovery Mode",
        }
        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f'  PLACED! Ticket: {result.order}')
        else:
            print(f'  FAILED: retcode={result.retcode if result else "None"}')
    else:
        reasons = []
        if not (all_bearish or all_bullish):
            reasons.append(f'TF not aligned: {trends}')
        if atr_h1 >= 20:
            reasons.append(f'ATR H1 {atr_h1:.2f} >= 20')
        print(f'\n  NO ENTRY - {"; ".join(reasons)}')

mt5.shutdown()
