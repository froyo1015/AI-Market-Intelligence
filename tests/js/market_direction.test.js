"use strict";

const assert = require("node:assert/strict");
const view = require("../../src/pages/static/intelligence.js");

function market(symbol, dailyChange, freshnessStatus = "current", status = "success") {
  return {symbol, dailyChange, freshnessStatus, status};
}

const groups = view.buildMarketDirection([
  market("DXY", 0.4),
  market("EURUSD", -0.2),
  market("SPY", -0.1),
  market("BTC-USD", 0.8),
  market("ETH-USD", 0),
  market("GOLD", 0.3)
]);

assert.deepEqual(groups.map(item => item.category), ["宏觀", "外匯", "美股", "Crypto", "商品"]);
const items = groups.flatMap(group => group.items);
assert.equal(items.length, 6);
assert.deepEqual(items.map(item => item.symbol), ["DXY", "EURUSD", "SPY", "BTC-USD", "ETH-USD", "GOLD"]);
assert.deepEqual(items.map(item => item.arrow + " " + item.state), [
  "↑ 偏強", "↓ 回落", "↓ 回落", "↑ 走高", "→ 持平", "↑ 走高"
]);

const stale = view.buildMarketDirection([market("SPY", 1.2, "stale")])
  .flatMap(group => group.items).find(item => item.symbol === "SPY");
assert.equal(stale.arrow, "—");
assert.equal(stale.state, "需要留意");

const missing = view.buildMarketDirection([]).flatMap(group => group.items);
assert(missing.every(item => item.state === "暫無資料"));
assert(missing.every(item => item.arrow === "—"));

const unknown = view.buildMarketDirection([market("DXY", 1, "unknown")])
  .flatMap(group => group.items).find(item => item.symbol === "DXY");
assert.equal(unknown.state, "時間待確認");

const visibleCopy = JSON.stringify(groups.concat([stale, unknown]));
assert(!visibleCopy.match(/buy|sell|bullish|bearish|observed|classifier|score|signal/i));
assert(!visibleCopy.match(/買入|賣出|做多|做空|目標價/));

console.log("market-direction presentation tests passed");
