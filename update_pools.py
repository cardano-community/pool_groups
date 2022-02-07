#!/bin/env python3
# Objective:
# - Identify pool as individual vs clusters without relying on self-declared elections
#   (which can easily be rigged using social nuances) from more than one source
# - Have strict tolerance: This may mean that a pool whose metadata is updated might take
#   a bit to show up due to the way offline-pool metadata information is designed. All
#   professional SPOs are expected to be aware of the time it takes for this update in metadata
#   aggregators and are expected to accept risk or keep both version of metadata valid for a period.
# - Any mismatch between providers is controlled at source and atleast raised via github issue by relevant pool operator.
#
# High-Level Flow:
# - Download all pool information to adapools_list
# - ADAPools and ADAStat provide their pool group information over API, download pool group information for each to adapools_js and adastat_js respectively
#   - adapools_js : Those not recognised as part of a group have adapools_js[<index for pool>].group = null
#   - adastat_js : Those not recognised as part of a group are not in the list
# - Process each pool in adapools_js
#   - If the pool is also present in adastat_js (which is list of pools who are also groups):
#     - Add pool to group , preferring naming convention from adapools list
#   - If adastat and adapools dont match, add it as discrepancy
#   - If they agree on pool being single pool operator, add it to spof 
# - Process each pool in adastat_js
#   - Add any pools not listed in adapools_js as discrepancy

import traceback, random, json, os, jsbeautifier
import urllib3
http = urllib3.PoolManager()
urllib3.disable_warnings()
jsonf='pool_clusters.json'
spof='singlepooloperators.json'
dscrpncyf='descrepancy.json'

def load_json(url):
  resp = http.request('GET', url, redirect=True)
  if str(resp.status) == "200":
    obj = json.loads(resp.data)
    return obj
  else:
    print("An error occurred while downloading group definition from ADAPools!")
    exit

def save_json(obj,jsonfile):
  """Save Object argument to JSON file argument."""
  if obj == "":
    return
  with open(jsonfile, 'w') as f:
    options = jsbeautifier.default_options()
    options.indent_size = 2
    options.preserve_newlines = False
    f.write(jsbeautifier.beautify(json.dumps(obj,indent=2,sort_keys=True),options))

def open_json(jsonfile):
  """Open JSON file argument and return it as object."""
  if not os.path.isfile(jsonfile):
    save_json({},jsonfile)
  with open(jsonfile, 'r') as f:
    obj = json.load(f)
  return obj

def main():
  adapools_js = load_json('https://js.adapools.org/groups.json')
  adapools_list = load_json('https://js.adapools.org/pools.json')
  adastat_js = load_json('https://adastat.net/rest/v0/poolscluster.json')
  mismatch,groups={},{}
  spo=[]
  for ap_pool in adapools_js:
    # If pool is present in adapools metadata list, process in groups
    if str(ap_pool['pool_id']) in adapools_list:
      matched=0
      pool_info={"pool_id": str(ap_pool['pool_id']), "ticker": str(adapools_list[str(ap_pool['pool_id'])]['db_ticker']), "name": str(adapools_list[str(ap_pool['pool_id'])]['db_name'])}
      for as_pool in adastat_js:
        if str(as_pool['pool_id']) == str(ap_pool['pool_id']):
          if ap_pool['group'] != None:
            # Both ADAStat and ADAPools treat pool as part of cluster
            if str(ap_pool['group']) not in groups:
              groups[str(ap_pool['group'])]=[]
            groups[str(ap_pool['group'])].append(pool_info)
          else:
            # ADAPools consider pool single pool op, but ADAStat does not
            mismatch[str(ap_pool['pool_id'])]={'adapools': None, 'adastat': as_pool['cluster_name']}
          matched=1
          break
      # If pool from ADAPools was not found in ADAStat, add group details to mismatch
      if matched == 0:
        if ap_pool['group'] != None:
          mismatch[str(ap_pool['pool_id'])]={'adapools': str(ap_pool['group']),'adastat': None}
        else:
          # If ADAPools thinks it's individual op and ADAStat does not have the pool info either in groups, they agree it is "Individual Operator"
          if ap_pool['group'] == None:
            spo.append(pool_info)
  for pool in adastat_js:
    matched=0
    # If adastat pool is in adapools
    for ap_pool in adapools_js:
      if ap_pool['pool_id'] == pool['pool_id']:
        # If match is found, it would have already been handled in first loop
        matched=1
        break
    if matched == 0:
      mismatch[str(pool['pool_id'])]={'adapools': None,'adastat': str(pool['cluster_name'])}

  save_json(groups, jsonf)
  save_json(spo,spof)
  save_json(mismatch,dscrpncyf)

main()
