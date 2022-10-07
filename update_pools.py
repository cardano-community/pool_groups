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
# - ADAPools and ADAStat provide their pool group information over API, download pool group information for each to adapools_js and adastat_js respectively.
#   Any manual additions to the list is in addendum.json, load it to manual_js.
#   - adapools_js : Those not recognised as part of a group have adapools_js[<index for pool>].group = null
#   - adastat_js : Those not recognised as part of a group are not in the list
#   - manual_js : Those reported manually as cluster, SPaaS participant, ..
# - Process each pool in adapools_js
#   - If the pool is also present in adastat_js (which is list of pools who are also groups):
#     - Add pool to group , preferring naming convention from adapools list
#   - If adastat and adapools dont match, add it as discrepancy
#   - If they agree on pool being single pool operator, add it to spo 
# - Process each pool in adastat_js
#   - Add any pools not listed in adapools_js as discrepancy
# - Process addendum.json

import json, os, jsbeautifier, traceback
import urllib3
http = urllib3.PoolManager()
urllib3.disable_warnings()
jsonf='pool_clusters.json'
spof='singlepooloperators.json'
addendumf='addendum.json'
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
  with open(jsonfile, 'r', encoding='utf-8') as f:
    obj = json.load(f)
  return obj

def main():
  try:
    adapools_js = load_json('https://js.adapools.org/groups.json')
    adapools_list = load_json('https://js.adapools.org/pools.json')
    adastat_js = load_json('https://api.adastat.net/rest/v0/poolscluster.json')
    manual_js = open_json(addendumf)
    mismatch,groups={},{}
    spo={}
    for ap_pool in adapools_js: # Process ADAPools definitions
      # If pool is present in adapools metadata list, process in groups
      if str(ap_pool['pool_id']) in adapools_list:
        matched=0
        if ap_pool['group'] == None: #ADAPools thinks this pool is single operator pool
          spo[str(ap_pool['pool_id'])]={"ticker": str(adapools_list[str(ap_pool['pool_id'])]['db_ticker']), "name": str(adapools_list[str(ap_pool['pool_id'])]['db_name'])}
        else: # Pool is part of cluster as peer ADAPools
          if str(ap_pool['group']) not in groups:
            groups[str(ap_pool['group'])]=[]
          groups[str(ap_pool['group'])].append({"pool_id": str(ap_pool['pool_id']), "ticker": str(adapools_list[str(ap_pool['pool_id'])]['db_ticker']), "name": str(adapools_list[str(ap_pool['pool_id'])]['db_name'])})
    for singlepoolid in list(spo):
      for pool in adastat_js: # Process ADAStat definitions
        if pool['pool_id'] == singlepoolid: # ADAStat thinks mentioned entry is part of cluster
          del spo[singlepoolid]
          mismatch[str(pool['pool_id'])]={'adapools': None,'adastat': str(pool['cluster_name'])}
      for poolgrp in manual_js: # Process addendum
        for pool in manual_js[poolgrp]['pools']:
          if pool == singlepoolid: # Match found for manual addendum to override single pool operator definition
            if singlepoolid in spo:
              del spo[singlepoolid]
            mismatch[str(pool)]={'addendum': str("Part of '" + str(poolgrp) + "', reason: " + str(manual_js[poolgrp]['comment'])) }
    save_json(groups, jsonf)
    save_json(spo,spof)
    save_json(mismatch,dscrpncyf)
  except Exception as e:
    print ("Exception: " + str(e) + str(traceback.print_exc()))
main()
