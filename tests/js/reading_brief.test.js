"use strict";
const assert = require("node:assert/strict");
const view = require("../../src/pages/static/intelligence.js");
function sample(values, freshness = "current") {
  const wrapper = {object_id:"int_signal", validation_status:"validated", payload:{signal_id:"sig_crypto", observed_values:values}};
  const daily = {status:"partial", freshness_status:freshness, cross_asset_signals:[wrapper], upcoming_events:[]};
  const top = {items:[{id:"top_crypto", sourceObjectId:"sig_crypto", rank:1, freshnessStatus:freshness, storyKey:"market_state:risk_off", headline:"DO NOT INFER FROM THIS TITLE"}]};
  return {daily, top};
}
const values = value => ["BTC-USD", "ETH-USD"].map(asset=>({asset,value,metric:"daily_change_pct"}));
function build(data) { return view.buildReadingBrief(data.daily,data.top,{mode:"deterministic_fallback"},[],null); }
assert.equal(build(sample(values(1))).stories[0].headline,"BTC／ETH 同步上升");
assert.equal(build(sample(values(-1))).stories[0].headline,"BTC／ETH 同步下降");
assert.equal(build(sample(values(0))).stories[0].headline,"BTC／ETH 同步持平");
assert(!build(sample(values(1))).summary.includes("Risk-Off"));
assert(!build(sample(values(1))).summary.includes("1%"));
const stale = build(sample(values(-1),"stale"));
assert.equal(stale.stories[0].current,false);
assert(!stale.summary.includes("同步下降"));
assert.equal(stale.watch.length,0);
const invalid = sample(values(-1)); invalid.daily.cross_asset_signals[0].validation_status="invalid";
assert.equal(build(invalid).stories[0].current,false);
const missing = sample(values(-1)); missing.top.items[0].sourceObjectId="absent";
assert.equal(build(missing).stories[0].current,false);
const unsupported = build(sample([{asset:"BTC-USD",metric:"price",value:100}]));
assert.equal(unsupported.stories[0].current,false);
const empty = view.buildReadingBrief(null,{items:[]},{},[],null);
assert(empty.summary.includes("暫時無法判定"));
assert(!empty.summary.includes("時間不同步"));
assert.equal(empty.stories.length,0);
assert(empty.limits.some(x=>x.includes("不代表未來沒有事件風險")));
const ordered = sample(values(1)); ordered.top.items.push({...ordered.top.items[0],id:"top_second",rank:2});
assert.deepEqual(build(ordered).stories.map(x=>x.id),["top_crypto","top_second"]);
assert.deepEqual(build(ordered).watch,[
  "留意「BTC／ETH 同步上升」的共同變化是否延續；以後續有效觀察核對。"
]);
assert(!JSON.stringify(build(sample(values(1)))).match(/買入|賣出|導致|必定|將會上漲/));
console.log("Reading brief grounding, missing/stale states, order and direction tests passed");
