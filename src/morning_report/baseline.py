"""Build a fixed Chinese Morning Report from validated, linked intelligence."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from src.brief.renderer_validator import validate_renderer_input
from src.top_intelligence.validator import validate_top_intelligence_artifact

ZONE = ZoneInfo('Asia/Taipei')
VERSION = 'morning_report_v1'
STATUS = {'risk_on': '較偏積極（Risk-On）', 'risk_off': '較偏防守（Risk-Off）',
          'mixed': '方向不一', 'unavailable': '暫無法判定'}


def instant(value):
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    if result.tzinfo is None:
        raise ValueError('aware timestamp required')
    return result.astimezone(timezone.utc)


def iso(value):
    return value.astimezone(timezone.utc).isoformat().replace('+00:00','Z')


def target_date(scheduled_at):
    local=instant(scheduled_at).astimezone(ZONE)
    if local.time().replace(tzinfo=None)!=time(8,30):
        raise ValueError('Morning Report slot must be 08:30 Asia/Taipei')
    return local.date()


def _manifest_ref(manifest, name, payload, source_bytes):
    records=[a for module in manifest['modules'] for a in module.get('artifacts',[])
             if a.get('path')==name]
    if len(records)!=1 or records[0].get('approved_for_publication') is not True:
        raise ValueError('source artifact absent or unapproved in manifest')
    digest=hashlib.sha256(source_bytes).hexdigest()
    if records[0].get('sha256')!=digest:
        raise ValueError('manifest source hash mismatch')
    if records[0].get('artifact_type')!=payload.get('artifact_type'):
        raise ValueError('manifest source type mismatch')
    if records[0].get('generated_at')!=payload.get('generated_at'):
        raise ValueError('manifest source timestamp mismatch')
    return dict(artifact=name,run_id=payload['run_id'],sha256=digest,
                generated_at=payload['generated_at'],source_timestamp=payload.get('source_timestamp'),
                freshness_status=payload.get('freshness_status','unknown'))


def _refs(item):
    refs=item.get('evidence_refs',{})
    if not isinstance(refs,dict):
        raise ValueError('item references missing')
    return {key:list(value) for key,value in refs.items()}


def _story(item):
    kind=item['type']
    assets=[a for a in item.get('related_assets',[]) if isinstance(a,str)][:4]
    if kind=='market_regime':
        name={'risk_on':'市場環境較偏積極（Risk-On）',
              'risk_off':'市場環境較偏防守（Risk-Off）',
              'mixed':'主要市場方向不一'}.get(item['story_key'].split(':')[-1], '市場環境暫無法判定')
        why='這是目前已驗證資料的分類，不能據此推斷下一段走勢。'
        watch='留意下一輪已驗證市場觀察是否維持相同方向。'
    elif kind=='cross_asset_signal':
        name=('、'.join(assets) if assets else '多項資產')+'出現共同變化'
        why='這項觀察涉及多個市場，值得對照各自的來源與觀察時間。'
        watch='留意下一輪資料中，相關市場是否仍出現同向變化。'
    elif kind=='upcoming_event':
        name='已排定的經濟事件值得留意'
        why='目前只確認來源所列的排程，公布內容和市場反應仍未知。'
        watch='留意官方發布內容，再核對後續市場觀察。'
    elif kind=='data_quality':
        name='部分市場資料尚不完整'
        why='缺漏資料限制了報告可描述的範圍。'
        watch='留意來源能否恢復，以及資料時間是否更新。'
    elif kind=='observed_market_stress':
        name='市場出現已驗證的壓力觀察'
        why='這是目前觀察到的狀態，並不預示未來走勢。'
        watch='留意下一輪資料中相關壓力是否仍然存在。'
    else:
        name='已驗證的市場觀察'
        why='這項觀察已通過來源及引用檢查；實際影響仍須結合其他資料。'
        watch='留意下一輪經驗證的資料。'
    return dict(item_id=item['item_id'],rank=item['rank'],source_type=kind,
                headline_zh=name,what_happened_zh=name+'。',why_it_matters_zh=why,
                watch_today_zh=watch,related_assets=assets,
                freshness_status=item['freshness_status'],validation_status=item['validation_status'],
                source_ids=list(item.get('source_refs',[])),evidence_refs=_refs(item),
                timestamps=item['timestamps'])


def _eligible(item, cutoff):
    if item.get('validation_status')!='validated' or item.get('freshness_status')!='current':
        return False
    if item['type']=='upcoming_event':
        scheduled=item.get('timestamps',{}).get('scheduled_at',[])
        return bool(scheduled) and all(instant(t)>=cutoff for t in scheduled)
    return True


def _source_current(refs, artifacts, cutoff):
    return bool(refs) and all(
        ref.get('source_timestamp') and ref.get('freshness_status')=='current' and
        0<=(cutoff-instant(ref['source_timestamp'])).total_seconds()<=int(
            artifact.get('stale_after_seconds',86400))
        for ref,artifact in zip(refs,artifacts))


def build(daily, top, manifest, daily_bytes, top_bytes, scheduled_at, generated_at,
          sample_only=False):
    cutoff=instant(scheduled_at)
    generated=instant(generated_at)
    report_date=target_date(scheduled_at)
    if generated<cutoff or generated.astimezone(ZONE).date()!=report_date:
        raise ValueError('generation outside scheduled report date')
    validate_renderer_input(daily)
    validate_top_intelligence_artifact(top,daily)
    if manifest.get('artifact_type')!='run_manifest' or not manifest.get('run_id'):
        raise ValueError('validated source manifest required')
    source_dates={report_date.isoformat(),(report_date-timedelta(days=1)).isoformat()}
    if daily['report_date']!=top['report_date'] or daily['report_date'] not in source_dates:
        raise ValueError('source report date outside morning window')
    if any(instant(x['generated_at'])>cutoff for x in (daily,top,manifest)):
        raise ValueError('source generated after morning cutoff')
    refs=[_manifest_ref(manifest,'daily_intelligence.json',daily,daily_bytes),
          _manifest_ref(manifest,'top_intelligence.json',top,top_bytes)]
    source_current=_source_current(refs,(daily,top),cutoff)
    available=source_current and daily['status']!='unavailable' and top['status']!='unavailable'
    selected=[_story(i) for i in top['items'] if _eligible(i,cutoff)][:3] if available else []
    regime=daily['market_regime']
    classification=regime.get('payload',{}).get('classification')
    regime_current=available and regime.get('validation_status')=='validated' and regime.get('data_status')!='unavailable'
    regime_name=STATUS.get(classification,'暫無法判定') if regime_current else '暫無法判定'
    headline=(f'基準時點的已驗證資料顯示，市場環境{regime_name}；以下保留當時重點與資料限制。'
              if regime_current and classification in STATUS else
              '目前證據不足以確認整體市場環境；以下只列出可追溯的已驗證觀察。')
    overnight_start=datetime.combine(report_date-timedelta(days=1),time(18),ZONE).astimezone(timezone.utc)
    overnight=[s for s in selected if any(overnight_start<=instant(t)<cutoff
        for t in s['timestamps'].get('observed_at',[]))]
    limitations=[]
    if daily['status']!='available' or top['status']!='complete':
        limitations.append('來源報告有部分資料缺漏；請留意各項證據與來源時間。')
    if not source_current:
        limitations.append('來源資料在晨報基準時點已過期或時間不明，不能代表目前市場。')
    if not selected:
        limitations.append('晨報基準時點沒有足夠的現行已驗證重點；不補造市場結論。')
    limitations.append('晨報固定於此基準時點；其後市場變化不會改寫本報告。')
    source_ids={source_id for story in selected for source_id in story['source_ids']}
    source_publishers={record['source_id']:record['publisher']
        for record in daily['provenance_catalog']['source_records']
        if record.get('source_id') in source_ids and record.get('publisher')}
    content=dict(today_market_one_sentence=headline,overnight_highlights=overnight,
        overnight_note_zh=('已按證據時間列出隔夜觀察。' if overnight else
                           '暫無足夠的已驗證隔夜觀察，不能推斷隔夜市場全貌。'),
        top_items=selected,market_regime=dict(classification=classification if regime_current else None,
            summary_zh='市場環境'+regime_name+'。' if regime_current else '市場環境暫無法判定，合資格證據不足。',
            object_id=regime['object_id'],evidence_refs=regime['evidence_refs']),
        known_limitations=limitations,
        evidence_refs=sorted({ref for story in selected for values in story['evidence_refs'].values() for ref in values}),
        source_names=sorted({source_publishers.get(source_id,source_id) for source_id in source_ids}))
    result=dict(version=VERSION,report_type='morning',report_date=report_date.isoformat(),
        baseline_for_date=report_date.isoformat(),generated_at=iso(generated),
        baseline_timestamp=iso(cutoff),timezone='Asia/Taipei',
        source_run_id=manifest['run_id'],source_artifact_refs=refs,
        source_report_date=daily['report_date'],source_generated_at=top['generated_at'],
        source_freshness_status='current' if source_current else 'stale',
        data_status='partial' if available and (daily['status']!='available' or top['status']!='complete')
          else 'available' if available else 'unavailable',
        immutable_for_day=True,sample_only=bool(sample_only),content=content)
    result['report_id']='morning_'+report_date.isoformat()+'_'+hashlib.sha256(
        json.dumps(result,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()[:20]
    validate(result)
    return result


def validate(report):
    required={'version','report_type','report_date','baseline_for_date','generated_at',
        'baseline_timestamp','timezone','source_run_id','source_artifact_refs',
        'source_report_date','source_generated_at','source_freshness_status',
        'data_status','immutable_for_day','sample_only','content','report_id'}
    if set(report)!=required or report['version']!=VERSION or report['report_type']!='morning' or report['timezone']!='Asia/Taipei' or report['immutable_for_day'] is not True:
        raise ValueError('invalid morning report contract')
    if report['report_date']!=report['baseline_for_date'] or target_date(report['baseline_timestamp']).isoformat()!=report['report_date']:
        raise ValueError('morning report date mismatch')
    if instant(report['generated_at'])<instant(report['baseline_timestamp']) or instant(report['source_generated_at'])>instant(report['baseline_timestamp']):
        raise ValueError('morning report point-in-time violation')
    if not report['source_artifact_refs'] or any(len(r['sha256'])!=64 for r in report['source_artifact_refs']):
        raise ValueError('source linkage missing')
    if report['data_status'] not in {'available','partial','unavailable'} or report['source_freshness_status'] not in {'current','stale'}:
        raise ValueError('invalid report status')
    if set(report['content'])!={'today_market_one_sentence','overnight_highlights','overnight_note_zh',
          'top_items','market_regime','known_limitations','evidence_refs','source_names'}:
        raise ValueError('invalid morning content')
    if len(report['content']['top_items'])>3:
        raise ValueError('Morning Report changed Top 3 bound')
    identity=dict(report)
    identity.pop('report_id')
    expected='morning_'+report['report_date']+'_'+hashlib.sha256(
        json.dumps(identity,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()[:20]
    if report['report_id']!=expected:
        raise ValueError('morning report identity mismatch')


def public_projection(report):
    validate(report)
    projection=dict(version=report['version'],report_type='morning',
        baseline_for_date=report['report_date'],generated_at=report['generated_at'],
        baseline_timestamp=report['baseline_timestamp'],timezone=report['timezone'],
        report_id=report['report_id'],data_status=report['data_status'],
        freshness_status=report['source_freshness_status'],
        source_run_id=report['source_run_id'],source_artifact_refs=report['source_artifact_refs'],
        source_report_date=report['source_report_date'],
        immutable_for_day=True,sample_only=report['sample_only'],content=report['content'])
    validate_public(projection)
    return projection


def validate_public(projection):
    allowed={'version','report_type','baseline_for_date','generated_at','baseline_timestamp',
             'timezone','report_id','data_status','freshness_status','source_run_id',
             'source_artifact_refs','source_report_date','immutable_for_day','sample_only','content'}
    if set(projection)!=allowed or projection['report_type']!='morning' or projection['version']!=VERSION or projection['immutable_for_day'] is not True:
        raise ValueError('invalid public Morning Report fields')
    if target_date(projection['baseline_timestamp']).isoformat()!=projection['baseline_for_date'] or instant(projection['generated_at'])<instant(projection['baseline_timestamp']):
        raise ValueError('invalid public Morning Report time')
    if projection['timezone']!='Asia/Taipei' or projection['data_status'] not in {'available','partial','unavailable'} or projection['freshness_status'] not in {'current','stale'}:
        raise ValueError('invalid public Morning Report status')
    if not projection['source_artifact_refs'] or any(ref['artifact'] not in {'daily_intelligence.json','top_intelligence.json'} or len(ref['sha256'])!=64
                for ref in projection['source_artifact_refs']):
        raise ValueError('unapproved public source reference')
    if len(projection['content']['top_items'])>3 or len(projection['content']['overnight_highlights'])>3:
        raise ValueError('public report content exceeds baseline scope')
