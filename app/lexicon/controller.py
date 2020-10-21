import json
import re

from app.projects.service import ProjectService
from app.user.service import UserService
from app.utils.grew_utils import grew_request
from flask import Response, abort, current_app, request
from flask_login import current_user
from flask_restx import Namespace, Resource, reqparse

api = Namespace(
    "Grew", description="Endpoints for dealing with samples of project"
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
            current_app,
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
class LexiconExportJson(Resource):
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
        patterns = []
        commands = []
        without = ""
        dic = {0: "form", 1: "lemma", 2: "upos", 3: "_MISC_Gloss", 4: "trait"}
        for i in lexicon:
            line1 = i["currentInfo"].split(" ")
            line2 = i["info2Change"].split(" ")
            comp += 1
            patterns.append(transform_grew_get_pattern(line1, dic, comp))
            resultat = transform_grew_verif(line1, line2)
            co, without_traits = transform_grew_get_commands(
                resultat, line1, line2, dic, comp
            )
            commands.append(co)
            if without_traits != "":
                without = without + without_traits
        patterns[0] = (
            "% click the button 'Correct lexicon' to update the queries\n\npattern { "
            + patterns[0][0:]
        )
        commands[0] = "commands { " + commands[0][0:]
        patterns[len(lexicon["data"]) - 1] += " }"
        commands.append("}")
        if len(without) != 0:
            without = "\nwithout { " + without + "}"
        patterns_output = ",".join(patterns)
        commands_output = "".join(commands)
        resp = {
            "patterns": patterns_output,
            "commands": commands_output,
            "without": without,
        }
        # print("patterns :", ','.join(patterns), "\ncommands :", ''.join(commands))
        resp["status_code"] = 200
        return resp


# TODO : It seems that this function is not finished. Ask Lila what should be done
@api.route("/<project_name>/upload/validator", methods=["POST", "OPTIONS"])
class LexiconUploadValidatorResource(Resource):
    def post(self, project_name):
        fichier = request.files["files"]
        f = fichier.read()
        resp = {"validator": f, "message": "hello"}
        resp["status_code"] = 200
        return resp


@api.route("/<project_name>/addvalidator")
class LexiconAddValidatorResource(Resource):
    def post(self, project_name: str):
        parser = reqparse.RequestParser()
        parser.add_argument(name="data", type=dict, action="append")
        parser.add_argument(name="validator", type=dict, action="append")
        args = parser.parse_args()
        lexicon = args.get("data")

        
        lexicon = args.get("data")
        validator = args.get("validator")
        list_validator = []
        line = []
        A = []
        B = []
        AB_Ok = []
        AB_Diff = []
        list_types = {
            "In the two dictionaries with the same information": AB_Ok,
            "In the two dictionaries with different information": AB_Diff,
            "Only in the old dictionary": A,
            "Only in the imported dictionary": B,
        }

        for i in validator["validator"].split("\n"):
            a = i.split("\t")
            if a[-1] == "":
                a.pop()
            if a != []:
                a[-1] = a[0] + a[1] + a[2] + a[3] + a[4]
                newjson = {
                    "form": a[0],
                    "lemma": a[1],
                    "POS": a[2],
                    "features": a[3],
                    "gloss": a[4],
                    "key": a[-1],
                }
                list_validator.append(newjson)
        # print("lexicon = \n", list_lexicon, "\n\nval = \n", list_validator)

        for x in lexicon["data"]:
            if "frequency" in x:
                del x["frequency"]
            for y in list_validator:
                if x["key"] == y["key"] and x not in AB_Ok and x not in AB_Diff:
                    AB_Ok.append(x)
                elif (
                    x["key"] != y["key"]
                    and x["form"] == y["form"]
                    and x not in AB_Ok
                    and x not in AB_Diff
                    and y not in AB_Ok
                    and y not in AB_Diff
                ):
                    AB_Diff.extend((x, y))

        for x in lexicon["data"]:
            if x not in AB_Ok and x not in AB_Diff and x not in A:
                A.append(x)
        for y in list_validator:
            if y not in AB_Ok and y not in AB_Diff and x not in B:
                B.append(y)

        for i in list_types:
            for s in list_types[i]:
                s["type"] = i
                line.append(s)
        # print(line)
        resp = {"dics": line, "message": "hello"}
        resp["status_code"] = 200
        return resp


################################################################################
##################                                        #######################
##################           Helpers functions            #######################
##################                                        #######################
################################################################################


def transform_grew_verif(ligne1, ligne2):  # Voir différences entre deux lignes
    liste = []
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
    pattern = "X" + str(comp) + '[form="' + ligne[0] + '"'
    for element in range(1, len(ligne)):
        if element == len(ligne) - 1:
            # print(element, ligne[element], dic[element])
            if ligne[element] != "_" and "=" in ligne[element]:  # features
                # upos="DET", Number=Sing, PronType=Dem, lemma="dat"
                mot = ligne[element].split("|")
                pattern = pattern + ", " + ", ".join(mot)
        else:
            pattern = pattern + ", " + dic[element] + '="' + ligne[element] + '"'
    pattern = pattern + "]"
    return pattern


def transform_grew_get_without(l, l2, comp):
    les_traits = ""
    mot = l.split("|")
    mot2 = l2.split("|")
    liste_traits = []
    # for i in mot :
    # 	if i not in mot2 and i !="_": # suppression de traits 1 non existant dans traits2
    # 		les_traits = les_traits+"del_feat X"+str(comp)+"."+i.split("=")[0]+';'
    for i in mot2:
        if i not in mot and i != "_":  # ajout traits2 non existant dans traits1
            les_traits = les_traits + "X" + str(comp) + "." + i + "; "
            liste_traits.append(i)
    # print(les_traits, liste_traits)
    # print (without, liste_traits, len(liste_traits))
    if len(liste_traits) == 0:
        liste_traits = False
    return les_traits, liste_traits


# def transform_grew_get_features(l2, comp):
# 	les_traits=""
# 	mot2 = l2.split("|")
# 	without = "without { X["
# 	liste_traits = []
# 	for i in mot2 :
# 		les_traits = les_traits+" X"+str(comp)+"."+i+";"
# 		liste_traits.append(i)
# 	without=without+", ".join(liste_traits)+"]}\n"
# 	#print (without, liste_traits, len(liste_traits))
# 	if len(liste_traits)==0 :
# 		without = False
# 	return les_traits, without


def transform_grew_traits_corriges(l, comp):  # lignes2[4]=="_"
    traits = ""
    mot = l.split("|")
    for i in mot:  # suppression des traits 1
        traits = traits + "del_feat X" + str(comp) + "." + i.split("=")[0] + "; "
    return traits


def transform_grew_get_commands(resultat, ligne1, ligne2, dic, comp):
    correction = ""
    commands = ""
    without_traits = ""
    list_traits2 = ""
    for e in resultat:
        if e == 4:  # si traits sont différents
            # try :
            if ligne2[e] != "_":
                if ligne2[e] != "":  # insertion des traits
                    list_traits2, without_traits = transform_grew_get_without(
                        ligne1[e], ligne2[e], comp
                    )
                    commands = commands + list_traits2
                    # print(without_traits) OK
            else:  # si on doit supprimer les traits de ligne1
                traits_a_supprimer = transform_grew_traits_corriges(ligne1[e], comp)
                commands = commands + traits_a_supprimer
            # except IndexError:
            # 	if len(ligne2) < 5:
            # 		traits_a_supprimer = transform_grew_traits_corriges(ligne1[e], comp)
            # 		commands=commands+traits_a_supprimer
            # 	elif len(ligne1) < 5:
            # 		list_traits2, without_traits = transform_grew_get_features(ligne2[e], comp)
            # 		commands=commands+list_traits2
            # 	pass
        else:  # si la différence n'est pas trait
            commands = (
                commands + "X" + str(comp) + "." + dic[e] + '="' + ligne2[e] + '"; '
            )
    if without_traits == False:
        correction = correction + commands
    else:
        correction = correction + commands
    return correction, list_traits2
