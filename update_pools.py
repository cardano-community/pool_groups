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
    koios_pool_list = []

    pool_range = range(0, 100000, 1000)
    for offset in pool_range:
       # print ("offset is %s" % offset)
       fetched = load_json('https://api.koios.rest/api/v0/pool_list?offset=' + str(offset) + '&limit=1000')
       koios_pool_list.extend(fetched)
       # print ("fetched %s entries" % len(fetched))
       if len(fetched) < 1000:
          break

    adastat_js = load_json('https://api.adastat.net/rest/v1/poolclusters.json')
    manual_js = open_json(addendumf)
    mismatch,groups={},{}
    spo={}

    # for now start off assuming every pool is single-operator, until discovered to be otherwise
    for koios_pool in koios_pool_list:
      spo[str(koios_pool['pool_id_bech32'])]={"ticker": str(koios_pool['ticker']), "name": str(koios_pool['pool_id_bech32'])}

    for singlepoolid in list(spo):
      # print ("pool id: %s" % singlepoolid)
      for pool in adastat_js['rows']: # Process ADAStat definitions
        if pool['pool_id_bech32'] == singlepoolid: # ADAStat thinks mentioned entry is part of cluster
          # print ("adastat thinks %s is in cluster" % singlepoolid)
          del spo[singlepoolid]
          groups[str(pool['pool_id_bech32'])]={'adastat': str(pool['cluster_name'])}

      for poolgrp in manual_js: # Process addendum
        for pool in manual_js[poolgrp]['pools']:
          if pool == singlepoolid: # Match found for manual addendum to override single pool operator definition
            if singlepoolid in spo:
              del spo[singlepoolid]
            mismatch[str(pool)]={'addendum': str("Part of '" + str(poolgrp) + "', reason: " + str(manual_js[poolgrp]['comment'])) }
    if len(groups) <= 100:
      print("Something went wrong, pool_group size was: " + str(len(groups)) )
      exit(1)
    save_json(groups, jsonf)
    save_json(spo,spof)
    save_json(mismatch,dscrpncyf)
  except Exception as e:
    print ("Exception: " + str(e) + str(traceback.print_exc()))
main()
