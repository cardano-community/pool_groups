#!/bin/env python3
import csv 
import json 

def csv2json(csvf, jsonf, json2f):
  data = {}
  rawdata = []
  with open(csvf, encoding='utf-8') as csvf:
    csvReader = csv.DictReader(csvf,delimiter=";")
    for rows in csvReader:
      rawdata.append(rows)
      hrows = rows.copy()
      key = "solo"
      if rows['cluster_name'] != "":
        key = rows['cluster_name']
      if not key in data:
        data[key]=[]
      del hrows['cluster_name']
      del hrows['cluster_id']
      data[key].append(hrows)
    with open(jsonf, 'w', encoding='utf-8') as jsonfo:
      jsonfo.write(json.dumps(data, indent=2))
    with open(json2f, 'w', encoding='utf-8') as jsonfo:
      jsonfo.write(json.dumps(rawdata, indent=2))

csv2json(r'pool_cluster.csv', r'pool_cluster.json', r'pool_list.json')
