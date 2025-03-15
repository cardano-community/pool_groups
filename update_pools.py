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
# - Download a list of all registered pools frm koios
# - BalanceAnalytics and ADAStat provide their pool group information over API, download pool group information for each to adastat_js and balance_js respectively.
#   Any manual additions to the list is in addendum.json, load it to manual_js.
#   - balance_js : Those not recognised as part of a group have balance_js[<index for pool>].group = null
#   - adastat_js : Those not recognised as part of a group are not in the list
#   - manual_js : Those reported manually as cluster, SPaaS participant, etc.
# - Process each pool in balance_js
#   - If the pool is also present in adastat_js (which is list of pools who are also groups):
#     - Add pool to group , preferring naming convention from balanceanalytics list
#   - If adastat and balanceanalytics dont match, add it as discrepancy
#   - If they agree on pool being single pool operator, add it to spo 
# - Process each pool in adastat_js
#   - Add any pools not listed in balance_js as discrepancy
# - Process addendum.json

import json, os, jsbeautifier, traceback
import urllib3
http = urllib3.PoolManager()
urllib3.disable_warnings()
clustersf='pool_clusters_new.json'
spof='singlepooloperators_new.json'
addendumf='addendum.json'
allf='spos.json'

def load_json(url):
  resp = http.request('GET', url, redirect=True)
  if str(resp.status) == "200":
    obj = json.loads(resp.data)
    return obj
  else:
    print("An error occurred while downloading group definition from url: " + url)
    print("  " + str(resp.data))
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
      fetched = load_json('https://api.koios.rest/api/v1/pool_list?select=pool_id_bech32,ticker,pool_status&pool_status=eq.registered&offset=' + str(offset) + '&limit=1000&order=pool_id_bech32.asc')
      koios_pool_list.extend(fetched)
      if len(fetched) < 1000:
        break

    try:
      adastat_js = load_json('https://api.adastat.net/rest/v1/poolclusters.json')
      balance_js = load_json('https://www.balanceanalytics.io/api/groupdata.json')
      #adastat_js = open_json('adastat.json')
      #balance_js = open_json('balanceanalytics.json')
    except Exception as e:
      print ("ERROR!! Unable to download data from upstream. Exception: " + str(e) + str(traceback.print_exc()))
    manual_js = open_json(addendumf)
    spos, bal_groups, as_groups = {},{},{}
    grplist, singlepooloperatorlist, spolist = [],[],[]

    # for now start off assuming every pool is single-operator, until discovered to be otherwise
    for koios_pool in koios_pool_list:
      poolid = koios_pool['pool_id_bech32']
      spos[poolid]={"pool_id_bech32": poolid, "ticker": koios_pool['ticker'], "group": None}
      # Process Balance Analytics entries
      bal_poollist=list(filter(lambda x:x['pool_hash']==poolid,balance_js[0]['pool_group_json']))
      if len(bal_poollist) == 0:
        spos[poolid]["balanceanalytics_group"] = None
      else:
        bal_pool = bal_poollist[0]
        spos[poolid]["balanceanalytics_group"] = bal_pool['pool_group']
        if bal_pool['pool_group'] != 'SINGLEPOOL':
          if bal_pool['pool_group'] not in bal_groups:
            bal_groups[bal_pool['pool_group']] = []
          bal_groups[bal_pool['pool_group']].append(poolid)
          spos[poolid]["group"] = bal_pool['pool_group']
      # Process adastat entries
      as_poollist=list(filter(lambda x:x['pool_id_bech32']==poolid,adastat_js['rows']))
      if len(as_poollist) == 0:
        spos[poolid]["adastat_group"] = None
      else:
        as_pool = as_poollist[0] # Process ADAStat's list definition
        spos[poolid]["adastat_group"] = as_pool['cluster_name']
        if as_pool['cluster_name'] not in as_groups:
          as_groups[as_pool['cluster_name']] = []
        as_groups[as_pool['cluster_name']].append(poolid)
        if spos[poolid]["group"] == None:
          spos[poolid]["group"] = as_pool['cluster_name']
      # Process addendum file
      for poolgrp in manual_js:
        for pool in manual_js[poolgrp]['pools']:
          if pool == poolid: # Match found for manual addendum to override single pool operator definition
            if poolid in spos and spos[poolid]["group"] == None:
              spos[poolid]["group"]=poolgrp

    # Loop through every pool in adastat group list, to fill in groupings from balance analytics
    for as_grp in as_groups:
      bal_grpname = None
      for as_pool in as_groups[as_grp]:
        if spos[as_pool]["balanceanalytics_group"] != "SINGLEPOOL" and spos[as_pool]["balanceanalytics_group"] != None:
          bal_grpname = spos[as_pool]["balanceanalytics_group"]
      for as_pool in as_groups[as_grp]:
        if bal_grpname != None:
          spos[as_pool]["group"] = bal_grpname

    for spo in sorted(spos):
      spolist.append(spos[spo])
      if spos[spo]["group"] != None:
        grplist.append(spos[spo])
      else:
        singlepooloperatorlist.append(spos[spo])

    if len(grplist) <= 100:
      print("Something went wrong, pool_group size was unexpectedly too low: " + str(len(grplist)) )
      exit(1)
    save_json(spolist, allf)
    save_json(grplist, clustersf)
    save_json(singlepooloperatorlist,spof)
  except Exception as e:
    print ("Exception: " + str(e) + str(traceback.print_exc()))
main()
