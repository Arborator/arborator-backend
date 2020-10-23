# Some utility functions for grew process
import json

import requests
from werkzeug.utils import secure_filename


def grew_request(fct_name, current_app, data={}, files={}):
    if current_app.config["ENV"] == "dev":
        server = "http://arborator-dev.grew.fr"
    elif current_app.config["ENV"] == "prod":
        server = "http://arborator.grew.fr"
    try:
        r = requests.post("%s/%s" % (server, fct_name), files=files, data=data)
        return json.loads(r.text)
    except requests.ConnectionError:
        print("Connection refused")
    except Exception as e:
        print("Uncaught exception, please report %s" % e)


# def upload_project(fileobject, currentApp, reextensions=None):
#     """
#     upload project into grew and filesystem (upload-folder, see Config). need a file object from request
#     Will compile reextensions if no one is specified (better specify it before a loop)
#     """

#     setAppContext(current_app)

#     if reextensions == None:
#         reextensions = re.compile(r"\.(conll(u|\d+)?|txt|tsv|csv)$")

#     filename = secure_filename(fileobject.filename)
#     sample_name = reextensions.sub("", filename)

#     # writing file to upload folder
#     fileobject.save(os.path.join(Config.UPLOAD_FOLDER, filename))

#     if sample_name not in samples:
#         # create a new sample in the grew project
#         print("========== [newSample]")
#         reply = grew_request(
#             "newSample", data={"project_id": project_name, "sample_id": sample_name}
#         )
#         print(reply)

#     else:
#         print("/!\ sample already exists")

#     with open(os.path.join(Config.UPLOAD_FOLDER, filename), "rb") as inf:
#         print("========== [saveConll]")
#         if import_user:
#             reply = grew_request(
#                 "saveConll",
#                 data={
#                     "project_id": project_name,
#                     "sample_id": sample_name,
#                     "user_id": import_user,
#                 },
#                 files={"conll_file": inf},
#             )
#         else:  # if no import_user has been provided, it should be in the conll metadata
#             reply = grew_request(
#                 "saveConll",
#                 data={"project_id": project_name, "sample_id": sample_name},
#                 files={"conll_file": inf},
#             )
#         print(reply)


# prod
# if (len(sys.argv) > 1 and sys.argv[1] == "local"):
#     server = 'http://localhost:8080'
# else:
#     server = 'http://arborator.grew.fr'

# with open('../../../application.json', 'r') as f: fileConfig = json.load(f)

# if fileConfig['mode'] == 'development': server = 'http://arborator-dev.grew.fr'
# elif fileConfig['mode'] == 'production': server = 'http://arborator.grew.fr'

# with app.app_context():
#     if current_app['ENV'] == 'development': server = 'http://arborator-dev.grew.fr'
#     elif current_app['ENV'] == 'production': server = 'http://arborator.grew.fr'
# dev
# server = 'http://arborator-dev.grew.fr'


# reply = grew_request ( 'getSamples', data = {'project_id': project.project_name} )
# print('REPLYYY', reply)


# print ("\n***************************************************************************\n")
# print ('========== [newProject]')
# print ('       ... project_id -> proj_1')
# reply = send_request ('newProject', data={'project_id': 'proj_1'})
# print (reply)

# print ("\n***************************************************************************\n")
# print ('========== [newSample]')
# print ('       ... project_id -> proj_1')
# print ('       ... sample_id -> sample_t6')
# reply = send_request ('newSample', data={'project_id': 'proj_1', 'sample_id': 'sample_t6' })
# print (reply)

# print ("\n***************************************************************************\n")
# print ('========== [saveConll] ')
# print ('       ... project_id -> proj_1')
# print ('       ... sample_id -> sample_t6')
# print ('       ... user_id -> _base')
# print ('       ... conll_file -> data/fr_gsd-ud-test_00006.conllu')
# with open('data/fr_gsd-ud-test_00006.conllu', 'rb') as f:
#     reply = send_request (
#         'saveConll',
#         data = {'project_id': 'proj_1', 'sample_id': 'sample_t6', 'user_id': 'kim' },
# #        data = {'project_id': 'proj_1', 'sample_id': 'sample_t6' },
#         files={'conll_file': f},
#     )
#     print (reply)

# print ("\n***************************************************************************\n")
# print ('========== [newSample]')
# print ('       ... project_id -> proj_1')
# print ('       ... sample_id -> sample_01_to_10')
# reply = send_request ('newSample', data={'project_id': 'proj_1', 'sample_id': 'sample_01_to_10' })
# print (reply)

# print ("\n***************************************************************************\n")

# print ('========== [saveConll] ')
# print ('       ... project_id -> proj_1')
# print ('       ... sample_id -> sample_01_to_10')
# print ('       ... user_id -> _base')
# print ('       ... conll_file -> data/fr_gsd-ud-train_00001_00010.conllu')
# with open('data/fr_gsd-ud-train_00001_00010.conllu', 'rb') as f:
#     reply = send_request (
#         'saveConll',
#         data = {'project_id': 'proj_1', 'sample_id': 'sample_01_to_10', 'user_id': '_base' },
#         files={'conll_file': f},
#     )
#     print (reply)


# print ("\n***************************************************************************\n")
# print ('========== [newProject]')
# print ('       ... project_id -> proj_2')
# reply = send_request ('newProject', data={'project_id': 'proj_2'})
# print (reply)

# print ("\n***************************************************************************\n")
# print ('========== [newSample]')
# print ('       ... project_id -> proj_2')
# print ('       ... sample_id -> sample_11_to_20')
# reply = send_request ('newSample', data={'project_id': 'proj_2', 'sample_id': 'sample_11_to_20' })
# print (reply)

# print ("\n***************************************************************************\n")

# print ('========== [saveConll] ')
# print ('       ... project_id -> proj_2')
# print ('       ... sample_id -> sample_11_to_20')
# print ('       ... user_id -> _base')
# print ('       ... conll_file -> data/fr_gsd-ud-train_00011_00020.conllu')
# with open('data/fr_gsd-ud-train_00011_00020.conllu', 'rb') as f:
#     reply = send_request (
#         'saveConll',
#         data = {'project_id': 'proj_2', 'sample_id': 'sample_11_to_20', 'user_id': '_base' },
#         files={'conll_file': f},
#     )
#     print (reply)

# print ("\n***************************************************************************\n")

# print ("\n***************************************************************************\n")
# print ('========== [newSample]')
# print ('       ... project_id -> proj_2')
# print ('       ... sample_id -> sample_21_to_30')
# reply = send_request ('newSample', data={'project_id': 'proj_2', 'sample_id': 'sample_21_to_30' })
# print (reply)

# print ('========== [saveConll] ')
# print ('       ... project_id -> proj_2')
# print ('       ... sample_id -> sample_21_to_30')
# print ('       ... user_id -> _base')
# print ('       ... conll_file -> data/fr_gsd-ud-train_00021_00030.conllu')
# with open('../../vieux/grew_server/test/data/kisspetit', 'rb') as f:
#     reply = send_request (
#         'saveConll',
#         data = {'project_id': 'proj_1', 'sample_id': 'kisspetit', 'user_id': 'rinema56@gmail.com'  },
#         files={'conll_file': f},
#     )
#     print (reply)

# print ("\n***************************************************************************\n")

# print ('========== [saveConll] ')
# print ('       ... project_id -> proj_1')
# print ('       ... sample_id -> sample_01_to_10')
# print ('       ... conll_graph -> data/bruno.conll')
# reply = send_request (
#     'saveConll',
#     data = {'project_id': 'proj_1', 'sample_id': 'sample_01_to_10' },
#     files={'conll_file': f},
# )
# print (reply)

# print ("\n***************************************************************************\n")

# print ('========== [getProjects]')
# reply = send_request ('getProjects')
# print (reply)

# print ("\n***************************************************************************\n")

# print ('========== [getSamples]')
# print ('       ... project_id -> proj_1')
# reply = send_request ('getSamples', data={'project_id': 'proj_1'})
# print (reply)

# print ("\n***************************************************************************\n")

# print ('========== [getSentences]')
# print ('       ... project_id -> proj_1')
# print ('       ... pattern -> "pattern {N[user, upos = NOUN]}"')
# reply = send_request ('getSentences', data={'project_id': 'proj_1', 'pattern': 'pattern {N[user, upos = NOUN]}'})
# print (reply)

# print ("\n***************************************************************************\n")

# print ('========== [eraseSample]')
# print ('       ... project_id -> proj_1')
# print ('       ... sample_id -> sample_01_to_10')
# reply = send_request ('eraseSample', data={'project_id': 'proj_1', 'sample_id': 'sample_01_to_10'})
# print (reply)

# print ("\n***************************************************************************\n")

# print ('========== [getSamples]')
# print ('       ... project_id -> proj_1')
# reply = send_request ('getSamples', data={'project_id': 'proj_1'})
# print (reply)

# print ("\n***************************************************************************\n")

# print ('========== [eraseProject]')
# print ('       ... project_id -> proj_2')
# reply = send_request ('eraseProject', data={'project_id': 'Marine test 2'})
# print (reply)

# print ("\n***************************************************************************\n")

# print ('========== [renameProject]')
# reply = send_request ('renameProject', data={'project_id': 'Naijaa', "new_project_id":"Naija"})
# print (reply)

# print ("\n***************************************************************************\n")

# print ('========== [getProjects]')
# reply = send_request ('getProjects')
# print (reply)

# print ('========== [getSamples]')
# print ('       ... project_id -> French')
# reply = send_request ('getSamples', data={'project_id': 'French'})
# print (reply)

# print ('========== [getSamples]')
# print ('       ... project_id -> Naija')
# reply = send_request ('getSamples', data={'project_id': 'Naija'})
# print (reply)

# print ('========== [getConll]')
# reply = send_request ('getConll', data={'project_id':'Naija', "sample_id":"P_ABJ_GWA_10_Steven.lifestory_PRO"})
# print (reply)


# print ('========== [getUsers]')
# reply = send_request ('getUsers', data={'project_id':'proj_1', "sample_id":'sample_t6'})
# print (reply)

# conll="""# sent_id = P_WAZK_07_As-e-dey-Hot-News-Read_PRO_1
# 1	dis	_	ADJ	_	PronType=Prox|Number=Sing|startali=1560|endali=1737	2	det	_	_
# 2	one	_	NOUN	_	NumType=Card|startali=1737|endali=1836	3	subj	_	_
# 3	na	_	PART	_	PartType=Cop|startali=1836|endali=1930	0	root	_	_
# 4	{	_	PUNCT	_	startali=1930|endali=1960	5	punct	_	_
# 5	short	_	ADJ	_	startali=1960|endali=2090	9	dep	_	_
# 6	|r	_	PUNCT	_	startali=2090|endali=2120	7	punct	_	_
# 7	short	_	ADJ	_	startali=2120|endali=2270	5	compound:redup	_	_
# 8	}	_	PUNCT	_	startali=2270|endali=2300	5	punct	_	_
# 9	tori	_	NOUN	_	startali=2300|endali=2480	3	comp:pred	_	_
# 10	wey	_	SCONJ	_	startali=2480|endali=2590	9	dep	_	_
# 11	dey	_	AUX	_	startali=2590|Aspect=Imp|endali=2696	10	comp	_	_
# 12	waka	_	VERB	_	startali=2696|endali=2940	11	comp:aux	_	_
# 13	come	_	VERB	_	startali=2940|endali=3110	12	compound:svc	_	_
# 14	your	_	ADJ	_	PronType=Prs|Number=Sing|Poss=Yes|startali=3110|Person=2|endali=3210	15	dep	_	_
# 15	domot	_	VERB	_	startali=3210|endali=3530	13	comp:obj	_	_
# 16	on	_	ADP	_	startali=3530|endali=3630	13	comp:obl	_	_
# 17	top	_	NOUN	_	startali=3630|endali=3750	16	fixed	_	_
# 18	{	_	PUNCT	_	startali=3750|endali=3780	19	punct	_	_
# 19	ninety	_	NUM	_	startali=3780|endali=4020	16	comp	_	_
# 20	five	_	NUM	_	NumType=Card|startali=4020|endali=4280	19	flat	_	_
# 21	point	_	NOUN	_	startali=4280|endali=4570	20	flat	_	_
# 22	one	_	NUM	_	NumType=Card|startali=4570|endali=4680	21	flat	_	_
# 23	Wazobia	_	PROPN	_	startali=4710|endali=5280	19	conj:appos	_	_
# 24	FM	_	PROPN	_	startali=5280|endali=5564	23	flat	_	_
# 25	}	_	PUNCT	_	startali=5564|endali=5594	19	punct	_	_
# 26	for	_	ADP	_	startali=5594|endali=5734	13	comp:obl	_	_
# 27	dis	_	DET	_	PronType=Prox|Number=Sing|startali=5734|endali=5860	30	det	_	_
# 28	number	_	NOUN	_	startali=5860|endali=6080	29	compound	_	_
# 29	five	_	NUM	_	NumType=Card|startali=6080|endali=6350	30	dep	_	_
# 30	day	_	NOUN	_	Number=Plur|startali=6350|endali=6490	26	comp	_	_
# 31	for	_	ADP	_	startali=6490|endali=6710	13	comp:obl	_	_
# 32	inside	_	ADP	_	startali=6710|endali=7082	31	fixed	_	_
# 33	dis	_	DET	_	PronType=Prox|Number=Sing|startali=7082|endali=7197	34	det	_	_
# 34	June	_	NOUN	_	startali=7197|endali=7390	31	comp	_	_
# 35	twenty	_	NUM	_	startali=7390|endali=7647	36	compound	_	_
# 36	seventeen	_	NUM	_	startali=7647|endali=8110	34	flat	_	_
# 37	//	_	PUNCT	_	startali=8110|endali=8140	3	punct	_	_
# """
# reply = send_request (
# 'saveGraph',
# data = {'project_id': "Naija", 'sample_id': "test_timestamp", 'user_id':'sy', "conll_graph":conll}
# )
# print(reply)
