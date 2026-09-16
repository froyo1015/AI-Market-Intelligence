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
assert.equal(build(sample(values(1))).stories[0].headline,"BTC 與 ETH 同步走高");
assert.equal(build(sample(values(-1))).stories[0].headline,"BTC 與 ETH 同步回落");
assert.equal(build(sample(values(0))).stories[0].headline,"BTC 與 ETH 同步持平");
assert(!build(sample(values(1))).summary.includes("Risk-Off"));
assert(!build(sample(values(1))).summary.includes("1%"));
const stale = build(sample(values(-1),"stale"));
assert.equal(stale.stories[0].current,false);
assert(!stale.summary.includes("同步回落"));
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
assert(empty.limits.some(x=>x.includes("不代表期間沒有事件風險")));
const ordered = sample(values(1)); ordered.top.items.push({...ordered.top.items[0],id:"top_second",rank:2});
assert.deepEqual(build(ordered).stories.map(x=>x.id),["top_crypto","top_second"]);
assert.deepEqual(build(ordered).watch,[
  "下一輪更新要看 BTC 與 ETH 是否繼續同向。"
]);
const chineseFirst = build(sample(values(-1))).stories[0];
assert(chineseFirst.what.includes("BTC回落"));
assert(chineseFirst.why.includes("主要加密資產"));
assert(chineseFirst.watch.includes("下一輪更新"));
assert(!chineseFirst.headline.includes("Observed"));
assert(![chineseFirst.headline,chineseFirst.what,chineseFirst.why,chineseFirst.watch].join(" ")
  .match(/deterministic|classifier|story key|coverage|score/i));
const scheduledAt = new Date(Date.now() + 3600000).toISOString();
const eventDaily = {
  status:"partial", freshness_status:"current", cross_asset_signals:[], upcoming_events:[{
    object_id:"int_event", validation_status:"validated", payload:{
      risk_id:"risk_event", category:"upcoming_event",
      observed_facts:{event_name:"U.S. CPI",country:"US",scheduled_at:scheduledAt}
    }
  }]
};
const eventTop = {items:[{
  id:"top_event",sourceObjectId:"risk_event",rank:1,freshnessStatus:"current",
  storyKey:"event:cpi",type:"upcoming_event",headline:"Upcoming official event: U.S. CPI"
}]};
const eventStory = build({daily:eventDaily,top:eventTop}).stories[0];
assert(eventStory.headline.startsWith("消費物價指數（CPI"));
assert(eventStory.what.includes("官方日曆"));
assert(eventStory.why.includes("未指向特定升跌方向"));
assert(!eventStory.headline.includes("Upcoming official event"));
const goldDollar = sample([
  {asset:"GOLD",value:1,metric:"daily_change_pct"},
  {asset:"DXY",value:-1,metric:"daily_change_pct"}
]);
const goldStory = build(goldDollar).stories[0];
assert.equal(goldStory.headline,"黃金走高、美元回落");
assert(goldStory.why.includes("不能證明因果"));
const equities = sample([
  {asset:"SPY",value:-1,metric:"daily_change_pct"},
  {asset:"QQQ",value:-1,metric:"daily_change_pct"}
]);
const equityStory = build(equities).stories[0];
assert.equal(equityStory.headline,"SPY 與 QQQ 同步回落");
assert(equityStory.why.includes("美股指數 ETF"));
function regimeScenario(classification) {
  const wrapper = {
    object_id:"int_regime", validation_status:"validated",
    payload:{run_id:"regime_run",classification}
  };
  return {
    daily:{status:"available",freshness_status:"current",market_regime:wrapper,cross_asset_signals:[],upcoming_events:[]},
    top:{items:[{
      id:"top_regime",sourceObjectId:"regime_run",rank:1,freshnessStatus:"current",
      storyKey:"market_state:"+classification,type:"market_regime",headline:"MACHINE HEADLINE"
    }]}
  };
}
function visibleCopy(reading) {
  return [reading.summary,reading.regime,reading.regimeExplanation]
    .concat(reading.stories.flatMap(s=>[s.headline,s.what,s.why,s.watch]),reading.watch,reading.limits)
    .join(" ");
}
const riskOff = build(regimeScenario("risk_off"));
assert.equal(riskOff.stories[0].headline,"目前市場偏向避險（Risk-Off）");
assert(riskOff.stories[0].what.includes("較偏防守"));
assert(riskOff.stories[0].why.includes("不代表下一步走向"));
assert(riskOff.summary.includes("除市場環境外"));
assert(!riskOff.summary.includes("未能整理出可靠的市場主線"));
const riskOn = build(regimeScenario("risk_on"));
assert.equal(riskOn.stories[0].headline,"目前市場偏向風險資產（Risk-On）");
assert(riskOn.stories[0].what.includes("較偏積極"));
assert(riskOn.stories[0].why.includes("不代表下一步走向"));
assert(riskOn.summary.includes("除市場環境外"));
assert.equal(empty.summary,"目前市場環境暫時無法判定。現有資料不足，今日暫未能整理出可靠的市場主線。");
assert(empty.regimeExplanation.includes("暫時不宜為市場定調"));
[riskOff,riskOn,empty].forEach(reading=>{
  const copy = visibleCopy(reading);
  assert(!copy.match(/deterministic|classifier|story[_ ]?key|coverage|score|confidence|rule[_ ]?id|signal[_ ]?id/i));
  assert(!copy.match(/買入|賣出|加倉|減倉|目標價|必然|必定|將會上升|將會下跌|\bbuy\b|\bsell\b/i));
  assert(reading.summary.length <= 100);
  reading.stories.forEach(story=>{
    assert(story.headline.length <= 40);
    assert(story.what.length <= 70);
    assert(story.why.length <= 70);
    assert(story.watch.length <= 70);
    assert.notEqual(story.what,story.why);
  });
});
assert(!JSON.stringify(build(sample(values(1)))).match(/買入|賣出|導致|必定|將會上漲/));
console.log("Reading brief grounding, missing/stale states, order and direction tests passed");
