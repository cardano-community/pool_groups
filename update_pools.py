#!/bin/env python3
import traceback, random, json, os
import urllib3
http = urllib3.PoolManager()
urllib3.disable_warnings()
jsonf='pool_clusters.json'
dscrpncyf='descrepancy.json'
def load_json(url):
  resp = http.request('GET', url, redirect=True)
  if str(resp.status) == "200":
    obj = json.loads(resp.data)
    return obj
  else:
    print("An error occurred while downloading group definition from ADAPools!")
    exit

def main():
  adapools_js = load_json('https://js.adapools.org/groups.json')
  adapools_list = load_json('https://js.adapools.org/pools.json')
  adastat_js = load_json('https://adastat.net/rest/v0/poolscluster.json')
  mismatch,groups={},{}
  mismatch['Individual Operators'],groups['Individual Operators']=[],[]
  for pool in adapools_js:
    matched=0
    for as_pool in adastat_js:
      if as_pool['pool_id'] == pool['pool_id']:
        matched=1
        break
    if matched == 0 and pool['group'] != None:
      mismatch[str(pool['pool_id'])]={'adapools': str(pool['group']),'adastat': None}
    if str(pool['pool_id']) in adapools_list:
      pool_info={"pool_id": str(pool['pool_id']), "ticker": str(adapools_list[str(pool['pool_id'])]['db_ticker']), "name": str(adapools_list[str(pool['pool_id'])]['db_name'])}
      if pool['group'] != None:
        if str(pool['group']) not in groups:
          groups[str(pool['group'])]=[]
        groups[str(pool['group'])].append(pool_info)
      else:
        groups['Individual Operators'].append(pool_info)
    else:
      mismatch[str(pool['pool_id'])]={'adapools': str(str(pool['group']) + " - not in list"),'adastat': None}
  for pool in adastat_js:
    matched=0
    isdiff=0
    for ad_pool in adapools_js:
      if ad_pool['pool_id'] == pool['pool_id']:
        matched=1
        if ad_pool['group'] == None:
          isdiff=1
        break
    if matched == 0 or isdiff == 1:
      mismatch[str(pool['pool_id'])]={'adapools': None,'adastat': str(pool['cluster_name'])}
      if str(pool['pool_id']) in adapools_list:
        pool_info={"pool_id": str(pool['pool_id']), "ticker": str(adapools_list[str(pool['pool_id'])]['db_ticker']), "name": str(adapools_list[str(pool['pool_id'])]['db_name'])}
        if str(pool['cluster_name']) not in groups:
          groups[str(pool['cluster_name'])]=[]
        groups[str(pool['cluster_name'])].append(pool_info)
      else:
        mismatch[str(pool['pool_id'])]={'adapools': "None - not in list",'adastat': str(pool['cluster_name'])}
  with open(jsonf, 'w', encoding='utf-8') as jsonfo:
      jsonfo.write(json.dumps(groups, indent=2, sort_keys=True))
  with open(dscrpncyf, 'w', encoding='utf-8') as dscrpncyfo:
      dscrpncyfo.write(json.dumps(mismatch, indent=2, sort_keys=True))
main()

