#!/bin/env python3
import traceback, random, json, os
import urllib3
http = urllib3.PoolManager()
urllib3.disable_warnings()
jsonf='pool_clusters.json'
def main():
  resp = http.request('GET', 'https://js.adapools.org/groups.json', redirect=True)
  if str(resp.status) == "200":
    adapools_js=json.loads(resp.data)
  else:
    print("An error occurred while downloading group definition from ADAPools!")
    return
  resp = http.request('GET', 'https://adastat.net/rest/v0/poolscluster.json', redirect=True)
  if str(resp.status) == "200":
    adastat_js=json.loads(resp.data)
  else:
    print("An error occurred while downloading cluster definition from ADAStat!")
    return
  i=1
  final={}
  final['Individual Operators']=[]
  for x in adastat_js:
    match_found=0
    for y in adapools_js:
      if x['pool_id'] == y['pool_id']:
        x.update(y)
        if str(x['group']) not in final:
          final[str(x['group'])]=[]
        if x['group']!=None:
          match_found=1
          final[str(x['group'])].append({"pool_id": str(x['pool_id']), "ticker": str(x['ticker']), "name": str(x['name'])})
        break
    if match_found == 0:
      final[str('Individual Operators')].append({"pool_id": str(x['pool_id']), "ticker": str(x['ticker']), "name": str(x['name'])})
  resp = http.request('GET', 'https://js.adapools.org/pools.json', redirect=True)
  if str(resp.status) == "200":
    pool_list = json.loads(resp.data)
  else:
    print("An error occurred while accessing pools list")
    return
  for x in pool_list:
    if pool_list[x]['pool_id_bech32'] not in final:
      final[str('Individual Operators')].append({"pool_id": pool_list[x]['pool_id_bech32'], "ticker": pool_list[x]['db_ticker'], "name": pool_list[x]['db_name']})
  with open(jsonf, 'w', encoding='utf-8') as jsonfo:
      jsonfo.write(json.dumps(final, indent=2, sort_keys=True))

main()
