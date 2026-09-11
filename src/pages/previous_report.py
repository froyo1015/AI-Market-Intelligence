"""Narrow presentation projection of a previous published market snapshot."""
import argparse
import json
import math
from pathlib import Path
from datetime import datetime


def project(payload):
    def time(value):
        if not isinstance(value, str):
            raise ValueError('timestamp unavailable')
        t = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if t.tzinfo is None:
            raise ValueError('timezone unavailable')
        return value
    result = {'generated_at': time(payload['generated_at']), 'records': []}
    symbols = {'SPY','QQQ','NVDA','AAPL','TSLA','BTC-USD','ETH-USD','GOLD','GC=F','EURUSD','EURUSD=X','USDJPY','JPY=X'}
    seen = set()
    for item in payload['records']:
        symbol = item.get('symbol')
        if symbol not in symbols or symbol in seen:
            continue
        seen.add(symbol)
        price = item.get('price')
        if type(price) not in (float,int) or not math.isfinite(price) or price < 0:
            continue
        if item.get('status') not in ('success','stale'):
            continue
        source = item.get('source')
        if source != 'yahoo_finance':
            continue
        result['records'].append({'symbol':symbol,'price':price,'timestamp':time(item['timestamp']),
                                  'source':source,'status':item['status']})
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True)
    p.add_argument('--target',required=True)
    args=p.parse_args()
    target=Path(args.target)
    target.unlink(missing_ok=True)
    result=project(json.loads(Path(args.source).read_text()))
    target.write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    main()
