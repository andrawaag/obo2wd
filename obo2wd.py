from wikidataintegrator import wdi_core, wdi_login
import json
import copy
from datetime import datetime
import requests
import os

print("Logging in...")
if "WDUSER" in os.environ and "WDPASS" in os.environ:
    WDUSER = os.environ['WDUSER']
    WDPASS = os.environ['WDPASS']
else:
    raise ValueError("WDUSER and WDPASS must be specified in local.py or as environment variables")
login = wdi_login.WDLogin(WDUSER, WDPASS)

ontologies = json.loads(requests.get("https://obofoundry.org/registry/ontologies.jsonld").text)

timeStringNow = datetime.now().strftime("+%Y-%m-%dT00:00:00Z")
refRetrieved = wdi_core.WDTime(timeStringNow, prop_nr="P813", is_reference=True)
obo_reference = wdi_core.WDUrl(value="https://obofoundry.org/", prop_nr="P854", is_reference=True)
obo_data_link = wdi_core.WDUrl(value="https://obofoundry.org/registry/ontologies.jsonld", prop_nr="P854", is_reference=True)
obo_reference = [obo_reference, obo_data_link, refRetrieved]

# Get licenses and their QIDs
licensesQids = dict()
for ontology in ontologies["ontologies"]:
  if "license" in ontology.keys():
   if ontology["license"]["label"] not in licensesQids.keys():
        try:
            licensesQids[ontology["license"]["label"]] = dict()
            licensesQids[ontology["license"]["label"]]["url"] = ontology["license"]["url"]
            query = f"""
                        SELECT * WHERE {{
                            ?item wdt:P2888 <{ontology["license"]["url"]}>  ;
                        }}"""
            results = wdi_core.WDFunctionsEngine.execute_sparql_query(query)
            print(query)
            licensesQids[ontology["license"]["label"]]["qid"] = results["results"]["bindings"][0]["item"]["value"]
        except:
            print("mismatch")

import sys

for ontology in ontologies["ontologies"]:
    if "homepage" in ontology.keys():
        escape_quote_ontology = ontology['title'].replace("'", "\\'")
    query = f"""
             SELECT * WHERE {{
                   {{?s rdfs:label '{escape_quote_ontology}'@en  . }}
                   UNION 
                   {{?s skos:altLabel '{escape_quote_ontology}'@en .}}
                   }}"""
    result = wdi_core.WDFunctionsEngine.execute_sparql_query(query)
    if (len(result["results"]["bindings"])) == 0:
        print(escape_quote_ontology, ontology['activity_status'])
        if ontology["activity_status"] == "active":
            print("ik kom hier")
            statements = []
            statements.append(
                wdi_core.WDItemID(value="Q324254", prop_nr="P31", references=[copy.deepcopy(obo_reference)]))
            statements.append(
                wdi_core.WDItemID(value="Q4117183", prop_nr="P361", references=[copy.deepcopy(obo_reference)]))

            # exact match
            if "homepage" in ontology.keys():
                if ontology["homepage"]:
                    try:
                        statements.append(wdi_core.WDUrl(value=ontology["homepage"], prop_nr="P856",
                                                         references=[copy.deepcopy(obo_reference)]))
                    except:
                        statements.append(wdi_core.WDUrl(value="https://" + ontology["homepage"], prop_nr="P856",
                                                         references=[copy.deepcopy(obo_reference)]))

            if "ontology_purl" in ontology.keys():
                statements.append(wdi_core.WDUrl(value=ontology["ontology_purl"], prop_nr="P2888",
                                                 references=[copy.deepcopy(obo_reference)]))

            # short name
            statements.append(wdi_core.WDMonolingualText(value=ontology["id"], prop_nr="P1813", language="mul",
                                                         references=[copy.deepcopy(obo_reference)]))
            # license
            if "license" in ontology.keys():
                statements.append(wdi_core.WDItemID(
                    value=licensesQids[ontology["license"]["label"]]["qid"].replace("http://www.wikidata.org/entity/",
                                                                                    ""), prop_nr="P275",
                    references=[copy.deepcopy(obo_reference)]))
            if "twitter" in ontology.keys():
                statements.append(wdi_core.WDString(value=ontology["twitter"], prop_nr="P5933",
                                                    references=[copy.deepcopy(obo_reference)]))

            # publications
            if "publication" in ontology.keys():
                pmidquery = f"""SELECT * WHERE {{
                               ?item wdt:P698 "{ontology["publication"]["id"].replace("https://www.ncbi.nlm.nih.gov/pubmed/", "")}" .
                            }}"""
                pmidresult = wdi_core.WDFunctionsEngine.execute_sparql_query(pmidquery)
                for pmidqid in pmidresult["results"]["bindings"]:
                    statements.append(
                        wdi_core.WDItemId(value=pmidqid["item"]["value"].replace("http://www.wikidata.org/entity", ""),
                                          prop_nr="P1343", references=[copy.deepcopy(obo_reference)]))

            item = wdi_core.WDItemEngine(new_item=True, data=statements)
            escape_quote_ontology = ontology['title'].replace("'", "\\'")
            item.set_label(escape_quote_ontology, lang="en")
            item.set_description("ontology part of OBOFoundry", lang="en")
            item.set_aliases(aliases=[ontology["id"]], lang="en")
            print(item.write(login))
            sys.exit("one more obo in wd")