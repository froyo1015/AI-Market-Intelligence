"""Static presentation copy only; never used by intelligence processors."""
import re

COPY = {
    'Market Intelligence View': '市場情報 · Beta',
    'AI Market Intelligence · Evidence View': 'AI Market Intelligence · 市場情報與證據',
    'Market Brief': '市場簡報', 'Intelligence': '市場情報',
    'Limited Beta · 10.2 candidate': '限量 Beta · 10.2 測試版',
    'Readiness: conditional · Last validation: 2026-09-12 05:46 UTC': '測試狀態：有條件開放 · 上次驗證：2026-09-12 05:46 UTC',
    'Beta release metadata': 'Beta 版本資訊',
    'Last validated deployed commit:': '上次通過部署驗證的版本：',
    '. This identifies the validated baseline, not an assertion that this candidate has been deployed.': '。此處記錄已驗證的基準版本，不代表本測試版已完成新的部署驗證。',
    'Current status unavailable; awaiting artifacts.': '正在讀取報告，目前暫無狀態資料。',
    'Data availability may vary. Unavailable and partial data are shown explicitly. This system provides evidence-backed market intelligence, not trading recommendations or a promise of prediction.': '系統整理已驗證的市場證據，提供有來源可查的市場情報。Beta 期間部分資料可能暫時無法取得，我們會明確標示缺漏。不提供買賣建議，也不承諾預測市場走勢。',
    'Send beta feedback on GitHub': '透過 GitHub 提交意見',
    'GitHub sign-in may be required. Feedback is public: do not include credentials, private account details or raw provider responses.': '可能需要登入 GitHub。意見會公開顯示，請勿提供密碼、API 金鑰、私人帳戶資料或供應商原始回應。',
    'Daily Intelligence Overview': '每日市場情報概覽', 'Market Intelligence': '市場情報',
    'Validated market relationships, current-condition regime and observable risks with a complete evidence trail.': '了解目前市場環境、跨市場變化及可觀察的風險，並追查每項資訊背後的證據。',
    'Market research you can trace': '每個觀察，都有證據可查',
    'AI Market Intelligence brings market observations, events and their supporting evidence into a daily research report.': '我們把市場數據、事件與相關來源整理成每日研究報告，方便你了解市場正在發生甚麼。',
    '1. Data — recorded observations': '1. 資料 — 記錄市場觀察', '2. Evidence — validated, traceable records': '2. 證據 — 驗證並保留來源', '3. Intelligence — structured context': '3. 情報 — 整理市場脈絡',
    'AI writes from validated intelligence when available; deterministic fallback is labeled. It does not choose the ranked stories, discover new facts, forecast prices or provide investment advice.': 'AI 只根據已驗證的情報撰寫簡報，不應自行補充不存在的事實，也不負責排名或預測價格。AI 無法使用時會標示規則式備援模式；所有內容均不構成投資建議。',
    'Daily research status unavailable': '今日報告狀態：暫無資料', 'Last update unavailable': '上次更新：暫無資料',
    'Research context only. Source freshness and report generation time are different checks.': '僅供研究參考。報告剛更新，不代表每項來源資料都是最新。',
    'Generated': '報告時間', 'Data status': '資料狀態', 'Freshness': '資料新鮮度（Freshness）', 'Validation': '資料驗證', 'Loading…': '讀取中…',
    'Daily Intelligence': '每日市場情報', 'Market Overview': '市場概覽', 'Macro &amp; Risk': '宏觀與風險', 'Risks Ahead': '未來風險', 'Crypto / Derivatives Shadow': '加密資產／衍生品測試', 'Evidence &amp; Methodology': '證據與研究方法',
    'New here? How to read this report': '第一次使用？如何閱讀這份報告',
    'Start with status and Executive Summary. Read What Changed, then Why It Matters. Review risks and open Evidence Trail to inspect references.': '先看資料狀態與今日市場摘要，再了解市場有何變化、為何重要。最後查看風險，展開證據與來源核對依據。',
    'Current meets the recorded freshness policy; stale is outside that window. Unknown means timing cannot be established. Unavailable means usable data is absent. A new report timestamp does not make old observations current.': '「目前有效」表示資料在指定時限內；「資料已過期」表示超出時限。「時間不明」表示無法判斷，「暫無資料」表示沒有可用記錄。請同時留意實際觀察時間。',
    'Validated means the record passed the applicable input and reference checks. It is not a guarantee of market truth or future outcomes.': '「已驗證」表示資料格式及引用通過檢查，不代表保證內容絕對正確，更不代表未來結果。',
    'Shadow Validated': 'Shadow 驗證中',
    'Derivatives records passed shadow checks but are not used for AI decisions. Passing readiness does not enable production.': '衍生品資料僅供測試觀察，尚未用於正式分析或 AI 決策。即使通過準備度檢查，也不會自動啟用。',
    'Missing modules': '部分資料缺漏',
    'Optional history or shadow data may be unavailable while other sections remain usable. No missing evidence is replaced with invented content.': '歷史或衍生品測試資料可能暫缺，其他有資料的章節仍可閱讀。系統不會自行編造證據來填補空白。',
    'Open Evidence Trail below': '查看下方證據與來源',
    '1. Executive Summary': '1. 今日市場摘要', 'Validated stories unavailable.': '暫無已驗證的市場重點。',
    '2. What Changed': '2. 市場有何變化',
    'Observed market snapshot differences only. No causal interpretation. Recorded status does not imply live data.': '僅比較兩次記錄中可觀察的變化，不推論因果；資料狀態不代表即時行情。',
    'Previous available run unavailable.': '暫無上次報告可供比較。',
    'AI MARKET BRIEF': 'AI 市場簡報', 'AI Market Brief': 'AI 市場簡報',
    'Validated narrative presentation of canonical intelligence artifacts': '根據已驗證市場情報整理的簡報',
    'Generation Mode': '簡報產生模式', 'Generated At': '產生時間', 'Loading validated brief…': '正在讀取已驗證簡報…',
    '3. Why It Matters': '3. 為何重要',
    "Today's Top Market Intelligence · Existing validated explanations and evidence": '今日市場重點 · 附已驗證的說明與證據',
    'Read the observation, why it matters, then what to monitor. Order and explanations come from validated artifacts; the page does not re-rank them. Scores are selection scores, not probabilities.': '依序閱讀市場觀察、重要性與後續觀察重點。排序沿用既有情報結果；分數用於選取重點，不是發生機率。',
    'Loading current priorities…': '正在讀取市場重點…',
    'Market Regime': '市場環境（Market Regime）', 'Current observed conditions only': '描述目前可觀察的環境，不預測未來', 'Loading validated regime…': '正在讀取市場環境…',
    'Cross Asset Signals': '跨資產觀察', 'Observed deterministic relationships only': '僅顯示規則辨識的共同變化，不代表買賣訊號', 'Loading observed relationships…': '正在讀取跨資產觀察…',
    '4. Market Structure': '4. 市場結構', 'Equity · Macro · Crypto · Existing market snapshots': '美股 · 宏觀 · 加密資產 · 已取得的行情記錄', 'Loading market observations…': '正在讀取行情…',
    'Derivatives Shadow': '衍生品（Derivatives）測試觀察', 'Shadow Validated · Not used for AI decisions': 'Shadow 驗證中 · 尚未用於 AI 決策',
    'Research preview only · Production disabled. Stale measurements are historical observations, not current evidence for decisions.': '僅供研究預覽 · 尚未用於正式分析。過期數值只是歷史觀察，不是目前市場的有效證據。', 'Derivatives unavailable.': '衍生品暫無資料。',
    '5. Risks Ahead': '5. 未來風險', 'Existing risk monitor: upcoming events, observed stress and data quality warnings': '留意即將發生的事件、已觀察到的市場壓力與資料缺漏', 'Loading observable risks…': '正在讀取風險資料…',
    '6. Evidence Trail': '6. 證據與來源', 'Evidence / Audit': '證據與來源查核', 'Loading provenance…': '正在讀取來源紀錄…',
    'Skip to daily research': '跳至今日市場摘要',
}


def localize_shell(page):
    # Exact text-node matching avoids modifying identifiers, code, links or CSS.
    def translate(match):
        value = match.group(1)
        stripped = value.strip()
        return '>' + (value.replace(stripped, COPY[stripped]) if stripped in COPY else value) + '<'
    page = re.sub(r'>([^<>]+)<', translate, page)
    for original, chinese in {
        'Primary': '主要導覽', 'Limited beta status': '限量 Beta 狀態',
        'Evidence-first architecture': '證據優先架構', 'Intelligence status': '市場情報狀態',
        'Research sections': '研究章節', 'AI brief publication metadata': 'AI 簡報發布資訊',
    }.items():
        page = page.replace('aria-label="' + original + '"', 'aria-label="' + chinese + '"')
    return page
