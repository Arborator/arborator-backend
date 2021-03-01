import json
import re
import os

from app.projects.service import ProjectService
from app.user.service import UserService
from app.utils.grew_utils import GrewService, grew_request
from flask import Response, abort, current_app, request
from flask_login import current_user
from flask_restx import Namespace, Resource, reqparse
from app.utils.conll3 import conll2tree, trees2conllFile
from app.config import Config
from app.samples.service import (
    SampleEvaluationService,
    SampleExerciseLevelService,
    SampleExportService,
    SampleRoleService,
    SampleUploadService,
)

api = Namespace(
    "Lexicon", description="Endpoints for dealing with samples of project"
)  # noqa


@api.route("/<string:project_name>/lexicon")
class LexiconResource(Resource):
    "Lexicon"

    def post(self, project_name: str):
        parser = reqparse.RequestParser()
        parser.add_argument(name="samplenames", type=str, action="append")
        parser.add_argument(name="treeSelection", type=str)
        args = parser.parse_args()

        sample_names = args.get("samplenames")
        treeSelection = args.get("treeSelection")
        print(sample_names, treeSelection)
        reply = grew_request(
            "getLexicon",
            data={"project_id": project_name, "sample_ids": json.dumps(sample_names)},
        )
        for i in reply["data"]:
            x = {"key": i["form"] + i["lemma"] + i["POS"] + i["features"] + i["gloss"]}
            i.update(x)
        resp = {"status_code": 200, "lexicon": reply["data"], "message": "hello"}
        return resp


@api.route("/<string:project_name>/export/json")
class LexiconExportJson(Resource):
    def post(self, project_name: str):
        parser = reqparse.RequestParser()
        parser.add_argument(name="data", type=dict, action="append")
        args = parser.parse_args()

        lexicon = args.get("data")
        for element in lexicon:
            del element["key"]
        line = json.dumps(lexicon, separators=(",", ":"), indent=4)
        resp = Response(line, status=200)
        return resp


@api.route("/<string:project_name>/export/tsv")
class LexiconExportTsv(Resource):
    def post(self, project_name: str):
        parser = reqparse.RequestParser()
        parser.add_argument(name="data", type=dict, action="append")
        args = parser.parse_args()
        lexicon = args.get("data")
        features = ["form", "lemma", "POS", "features", "gloss", "frequency"]
        line = ""
        for i in lexicon:
            for f in features:
                try:
                    line += i[f] + "\t"
                except TypeError:
                    line += str(i[f])
            line += "\n"

        resp = Response(line, status=200)
        return resp


@api.route("/<project_name>/transformationgrew")
class TransformationGrewResource(Resource):
    def post(self, project_name: str):
        parser = reqparse.RequestParser()
        parser.add_argument(name="data", type=dict, action="append")
        args = parser.parse_args()
        lexicon = args.get("data")
        comp = 0
        list_rules = str()
        rule = str()
        dic = {
            0: "form",
            1 : "lemma",
            2 : "upos",
            3 :"Gloss",
            4 : "trait"
            }

        for i in lexicon :
            pattern = "pattern { "
            command = "commands { "
            without = "without { "
            line1 = i['currentInfo'].split(' ')
            line2 = i['info2Change'].split(' ')
            comp+=1
            pattern += transform_grew_get_pattern(line1, dic, comp) + " }"
            resultat = transform_grew_verif(line1, line2)
            co, without_traits = (transform_grew_get_commands(resultat, line1, line2, dic, comp))
            command += co + "}"
            if without_traits == "":
                rule = pattern + " " + command
            else:
                without += without_traits + " }"
                rule = pattern + " " + without + " " + command
            if i == lexicon[0]:
                list_rules += rule
            else:
                list_rules += ",\n" + rule
        
        resp = {
            "rules": list_rules,
        }
        print(list_rules)
        resp["status_code"] = 200
        return resp


# TODO : It seems that this function is not finished. Ask Lila what should be done 
@api.route("/<project_name>/upload/validator", methods=["POST", "OPTIONS"])
class LexiconUploadValidatorResource(Resource):
    def post(self, project_name):
        file = request.files['files'].read()
        file = json.dumps(file.decode("utf-8"))
        resp = {"validator": file, "message": "hello"}
        resp["status_code"] = 200
        return resp


@api.route("/<project_name>/addvalidator")
class LexiconAddValidatorResource(Resource):
    def post(self, project_name: str):
        parser = reqparse.RequestParser()
        parser.add_argument(name="data", type=dict, action="append")
        parser.add_argument(name="validator", type=str, action="append")
        print("ok")

        args = parser.parse_args()
        lexicon = args.get("data")
        validator = json.loads(args.get("validator")[0])
        list_validator = []
        line = []
        A = []
        B = []
        AB_Ok = []
        AB_Diff = []
        list_types = {
            "In the two dictionaries with the same information" : AB_Ok,
            "Identical form in both dictionaries with different information" : AB_Diff,
            "Only in the old dictionary" : A,
            "Only in the imported dictionary" : B
        }
        
        for i in validator.split('\n'):
            a = i.split("\t")
            if a[-1] == '': 
                a.pop()
            if a != []: 
                a[-1] = a[0] + a[1] + a[2] + a[3] + a[4]
                newjson = {
                    "form":a[0],
                    "lemma":a[1],
                    "POS":a[2],
                    "features":a[3],
                    "gloss":a[4],
                    "key":a[-1],
                    }
                list_validator.append(newjson)

        for x in lexicon:
            if 'frequency' in x: 
                del x['frequency']
            for y in list_validator:
                # le token existe dans les deux dicts avec les mêmes feats
                if x['key'] == y['key'] and x not in AB_Ok and x not in AB_Diff: 
                    AB_Ok.append(x)
                    
                # le terme existe dans les deux dictionnaires mais avec de différents feats
                elif x['key'] != y['key'] and x['form'] == y['form'] and x not in AB_Ok and x not in AB_Diff and y not in AB_Ok and y not in AB_Diff: 
                    x['toChange'] = y['form'] + ' ' + y['lemma'] + ' ' + y['POS'] + ' ' + y['gloss'] + ' ' + y['features']
                    AB_Diff.extend((x,y))
                    print(x, "------->", y)

        # le token n'existe pas dans le dict B
        for x in lexicon:
            if x not in AB_Ok and x not in AB_Diff and x not in A:
                A.append(x)

        # le token n'existe pas dans le dict A
        for y in list_validator:
            if y not in AB_Ok and y not in AB_Diff and x not in B: 
                B.append(y)

        for i in list_types:
            for s in list_types[i]:
                s['type'] = i
                line.append(s)
                if 'toChange' not in s:
                    s['toChange'] = '_'
        resp = {"dics": line, "message": "hello"}
        resp["status_code"] = 200
        return resp



@api.route("/<string:project_name>/try-rules")
class TryRulesResource(Resource):
    def post(self, project_name: str):
        """
        expects json with grew pattern such as
        {
        "pattern":"pattern { N [upos=\"NUM\"] }"
        "rewriteCommands":"commands { N [upos=\"NUM\"] }"
        }
        important: simple and double quotes must be escaped!

        returns:
        {'sample_id': 'P_WAZP_07_Imonirhuas.Life.Story_PRO', 'sent_id': 'P_WAZP_07_Imonirhuas-Life-Story_PRO_97', 'nodes': {'N': 'Bernard_11'}, 'edges': {}}, {'sample_id':...
        """

        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)

        # TODO : to change
        if not request.json:
            abort(400)

        parser = reqparse.RequestParser()
        parser.add_argument(name="rules", type=str)
        parser.add_argument(name="sampleId", type=str)
        args = parser.parse_args()
        rules = args.get("rules")
        sampleId = args.get("sampleId")
        
        print(rules)
        print("sampleID :", sampleId)
        list_sampleIds = [id for id in sampleId.split(", ")]
        list_rules = [rule for rule in rules.split(",\n")]

        print("liste des règles : ",list_rules)
        print("liste des ids : ", list_sampleIds)
        trees = {}
        
        for sampleId in list_sampleIds:
            reply = grew_request(
                "tryRules",
                data={
                    "project_id":project_name,
                    "sample_id":sampleId,
                    "rules":json.dumps(list_rules)
                },
            )

            if reply["status"] != "OK":
                if "message" in reply:
                    resp = {
                        "status_code": 444,
                        "status": reply["status"],
                        "message": reply["message"],
                    }
                    status_code = 444
                    return resp
                abort(400)

            for m in reply["data"]:
                
                if m["user_id"] == "":
                    abort(409)
                print("___")
                if sampleId not in m["sample_id"]: continue
                trees[m["sample_id"]] = trees.get(m["sample_id"], {})
                trees[m["sample_id"]][m["sent_id"]] = trees[m["sample_id"]].get(
                    m["sent_id"], {"conlls": {}, "nodes": {}, "edges": {}}
                )
                trees[m["sample_id"]][m["sent_id"]]["conlls"][m["user_id"]] = m["conll"]
                if "sentence" not in trees[m["sample_id"]][m["sent_id"]]:
                    trees[m["sample_id"]][m["sent_id"]]["sentence"] = conll2tree(
                        m["conll"]
                    ).sentence()
        resp = {"status_code": 200, "trees": trees, "rules": list_rules}
        return resp



@api.route("/<string:project_name>/saveConll")
class SaveConll(Resource):
    def post(self, project_name: str):
        parser = reqparse.RequestParser()
        parser.add_argument(name="data", type=dict, action="append")
        args = parser.parse_args()
        data = args.get("data")
        sample_names = [ sampleId for sampleId in data[0] ]
        conll = str()

        for sample_name in sample_names:
            reply = grew_request(
                "getConll",
                data={"project_id": project_name, "sample_id": sample_name},
            )
            if reply.get("status") == "OK":

                sample_tree = SampleExportService.servSampleTrees(reply.get("data", {}))
                trees = list()
                for sent in sample_tree:
                    tree = dict()
                    if sent in data[0][sample_name]:
                        sample_tree[sent] = data[0][sample_name][sent]
                        tree[sent] = sample_tree[sent]
                    for user in sample_tree[sent]["conlls"]:
                        conll += sample_tree[sent]["conlls"][user] + "\n\n"

                file_name = sample_name + "_modified.conllu"
                path_file = os.path.join(Config.UPLOAD_FOLDER, file_name)
                with open(path_file, "w") as file:
                    file.write(conll)
            
                with open(path_file, "rb") as file_to_save:
                    GrewService.save_sample(project_name, sample_name, file_to_save)

            else:
                print("Error: {}".format(reply.get("message")))




################################################################################
##################                                        #######################
##################           Helpers functions            #######################
##################                                        #######################
################################################################################


def transform_grew_verif(ligne1, ligne2): #Voir différences entre deux lignes
	liste=[]
	if len(ligne1) > len(ligne2): 
		maximum = len(ligne1)
	else: 
		maximum = len(ligne2)
	for i in range(maximum):
		try:
			if ligne1[i] != ligne2[i]:
				liste.append(i)
		except IndexError:
			liste.append(i)
	return liste


def transform_grew_get_pattern(ligne, dic, comp): 
	pattern = "X" + str(comp) + '[form=\"' + ligne[0] + '\"'
	for element in range(1,len(ligne)):
		if element == len(ligne)-1:
			if ligne[element] != "_" and '=' in ligne[element]: #features
				mot = ligne[element].split("|") #Number=Sing, PronType=Dem
				pattern = pattern + ", " + ", ".join(mot)
		elif element == 2: # upos = PRON
			pattern = pattern + ", " + dic[element] + "=" + ligne[element]
		else:
			pattern = pattern + ", " + dic[element] + '=\"' + ligne[element] + '\"' # forme=\"dat\", lemma=\"dat\"
	pattern = pattern + "]"
	return pattern


def transform_grew_get_without(l, l2, comp):
	mot = l.split("|")
	mot2 = l2.split("|")
	les_traits = []
	liste_traits = []
	feats_str = ""
	# for i in mot :
	# 	if i not in mot2 and i !="_": # suppression de traits 1 non existant dans traits2
	# 		les_traits = les_traits+"del_feat X"+str(comp)+"."+i.split("=")[0]+';'
	for i in mot2:
		if i not in mot and i != "_": # ajout traits2 non existant dans traits1
			liste_traits.append(i)
	if len(liste_traits) == 0:
		feats_str = False
	if liste_traits:
		les_traits.append("X" + str(comp) + "[" + ",".join(liste_traits) + "]")
		for feat in liste_traits:
			feats_str += "X" + str(comp) + "." + feat + "; "
	return les_traits, feats_str



def transform_grew_traits_corriges(l, l2, comp): # différence entre deux feats
	traits = ''
	mot1 = l.split("|")
	print(mot1, l,l2)
	if l2 == "_":
		for i in mot1:
			traits = traits + "del_feat X" + str(comp) + "." + i.split("=")[0] + '; '
	else:
		mot2 = l2.split("|")
		print(mot2)
		for i in mot1:  # suppression des traits 1
			if i not in mot2:
				traits = traits + "del_feat X" + str(comp) + "." + i.split("=")[0] + '; '
	return traits


def transform_grew_get_commands(resultat, ligne1, ligne2, dic, comp):
	correction = ""
	commands = ""
	list_traits2 = []
	without = ""
	for e in resultat:
		if e == 4: #si traits sont différents
			if ligne2[e] != "_" and len(ligne1[e].split("|")) < len(ligne2[e].split("|")) or ligne1[e] == "_":
				if ligne2[e] != "": #insertion des traits
					list_traits2, feats_str = transform_grew_get_without(ligne1[e], ligne2[e], comp)
					without = ",".join(list_traits2)
					commands = commands + feats_str
			else: #si on doit supprimer les traits de ligne1 :
				traits_a_supprimer = transform_grew_traits_corriges(ligne1[e], ligne2[e], comp)
				commands = commands + traits_a_supprimer
		else: # si la différence n'est pas trait
			commands = commands + "X" + str(comp) + "." + dic[e] + '=\"' + ligne2[e] + '\"; '
	correction = correction + commands
	return correction, without