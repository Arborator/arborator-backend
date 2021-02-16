#!/usr/bin/python
# -*- coding: utf-8 -*-


# Modified by Marine Courtin for python3
#

####
# Copyright (C) 2009-2017 Kim Gerdes
# kim AT gerdes. fr
# http://arborator.elizia.net/
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of version 3 of the GNU Affero General Public License (the "License")
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This script is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE
# See the GNU General Public License (www.gnu.org) for more details.
#
# You can retrieve a copy of of version 3 of the GNU Affero General Public License
# from http://www.gnu.org/licenses/agpl-3.0.html
####
""" Kim's module to do conll <-> tree conversion and manipulate trees"""

import collections, re, glob
import copy


class Tree(dict):
	def __init__(self, *args, **kwargs):
		self.update(*args, **kwargs)
		self.sentencefeatures = {}
		self.words = []

	def __getitem__(self, key):
		val = dict.__getitem__(self, key)
		return val

	def __setitem__(self, key, val):
		dict.__setitem__(self, key, val)

	def __repr__(self):
		representation = "Tree: "+" ".join(self.words)+"\n"
		for f,v in self.sentencefeatures.items():
			representation += "# "+f+" = "+v+"\n"
		for i in self: # nodes
			representation += str(i)+": "+self[i].get("t","_")+"\t"+str(self[i])+"\n"
		return representation

	def update(self, *args, **kwargs):
		for k, v in dict(*args, **kwargs).items():
			self[k] = v

	def sentence(self):
		if self.words==[]:
			self.words = [self[i].get("t","") for i in sorted(self)]
			return u" ".join(self.words)
		else:
			s = " ".join([self[i]["t"] for i in self.keys()])
			return s

	def conllu(self):
		treestring = ""
		if self.sentencefeatures:
			for stftkey in sorted(self.sentencefeatures):
				if stftkey=="_comments":
					treestring+="# "+self.sentencefeatures[stftkey]
				else:
					treestring+="# "+stftkey+" = "+self.sentencefeatures[stftkey]+"\n"
		for i in sorted(self.keys()):
			node = self[i]
			govs=node.get("gov",{})
			govk = sorted(govs.keys())
			if govk:
				gk,gv = str(govk[0]),govs.get(govk[0],"_")
				if gk == "-1":
					gk = "_"
			else:
				gk,gv = "_","_"
			if 'feats' in node:
				treestring+="\t".join([str(i),node.get("t","_"),node.get("lemma","_"),node.get("tag","_"),node.get("xpos","_"),node.get('feats', "_"),gk,gv,"|".join( [ str(g)+":"+govs.get(g,"_") for g in govk[1:] ]) or "_",node.get("misc","_")]) + "\n"
			else:
				# print([ (a,v) for a,v in node.items()])
				treestring+="\t".join([str(i),node.get("t","_"),node.get("lemma","_"),node.get("tag","_"),node.get("xpos","_"),"|".join(sorted( [ a+"="+v for a,v in node.items() if a not in ["kids", "t","lemma","tag","tag2","xpos","egov","misc","id","index","gov"]]) or "_"),gk,gv,"|".join( [ str(g)+":"+govs.get(g,"_") for g in govk[1:] ]) or "_",node.get("misc","_")]) + "\n"
		return treestring

	def addkids(self, exclude=[]):
		"""
		adds dictionary to each node: 'kids': {1: 'dobj', 2: 'aux', 3: 'nsubj', 5: 'prep', 9: 'punct'}
		"""
		for i in self:
			self[i]['kids'] = {}
			# print(i)
		for i in self:
			for g,f in self[i].get("gov",{}).items():
				if f in exclude: continue
				if g>0: self[g]["kids"][i]=f
				else: self.rootnode=i

	def get_root(self):
		"""
		Finds the id of the root node inside the Tree

		Parameters
		----------
		self: Tree
			a dependency Tree in dict format

		Warning
		----------
		Assumes there is only one root, if there are several it will only return the first one.
		The root has a governor-id of value 0

		Returns
		----------
		num : int
			the id of the root node
		"""
		for num in self:
			node = self.get(num)
			if self.is_root(node):
				return num

	def is_root(self, node):
		"""
		Checks whether a node is the root of a tree

		Parameters
		----------
		self: Tree
			a dependency Tree in dict format
		node: dict
			the dict representation of the node

		Returns
		----------
		Boolean : True (is root) / False (is not root)
		"""
		if 0 in node["gov"]:
			return True
		else:
			return False

	def idgovRel(self,i):
		return list(self[i]["gov"].items())[0]


def update(d, u):
	for k, v in u.items():
		if isinstance(v, collections.Mapping):
			r = update(d.get(k, {}), v)
			d[k] = r
		else:
			d[k] = u[k]
	return d


def conll2tree(conllstring):
	tree=Tree()
	nr=1
	skipuntil=0 # only used to get the right "words" sequence, doesn't touch the actual tokens
	for line in conllstring.split('\n'):
		if line.strip():
			if line.strip()[0]=="#": # comment of conllu
				if "=" in line:
					tree.sentencefeatures[line.split("=")[0].strip()[1:].strip()]="=".join(line.split("=")[1:]).strip()
				else:
					tree.sentencefeatures["_comments"]=tree.sentencefeatures.get("_comments","")+line.strip()[1:]+"\n"
				continue

			cells = line.split('\t')
			nrCells = len(cells)


			if nrCells in [4,10,12, 13,14]:

				# if nrCells == 4: # malt!
				# 	t, tag, head, rel = cells
				# 	if head=="_": head=-1
				# 	else:head = int(head)
				# 	newf={'id':nr,'t': t, 'tag': tag,'gov':{head: rel}}
				# 	tree[nr]=update(tree.get(nr,{}), newf)
				# 	nr+=1

				if nrCells == 10: # standard conll 10 or conllu
					nr, t, lemma , tag, xpos, features, head, rel, edeps, misc = cells
					if "-" in nr or "." in nr:
						try:
							skipuntil=int(nr.split("-")[-1])
						except:
							skipuntil=float(nr.split("-")[-1])
						tree.words+=[t]
						continue
					try:
						nr = int(nr)
					except:	nr = float(nr) # handling the 3.1 format for "emtpy nodes"
					if head.strip()=="_": head=-1
					else:
						try:
							head = int(head)
						except:
							head = float(head)
					egov={}
					if ":" in edeps: # the enhanced graph is used
						egov=dict([(gf.split(":")[0],gf.split(":")[-1]) for gf in edeps.split("|")])

					newf={'id':nr,'t': t,'lemma': lemma, 'tag': tag, 'xpos': xpos, 'gov':{head: rel}, 'egov':egov, 'misc': misc}
					if "=" in features:
						mf=dict([(av.split("=")[0],av.split("=")[-1]) for av in features.split("|")])
						newf=update(mf,newf)

					tree[nr]=update(tree.get(nr,{}), newf)
					if nr>skipuntil: tree.words+=[t]

				if nrCells == 12: # elan format
					nr, t, lemma , tag, xpos, features, head, rel, edeps, unknown, misc1, misc2 = cells
					if "-" in nr:
						try:
							skipuntil=int(nr.split("-")[-1])
						except:
							skipuntil=float(nr.split("-")[-1])
						tree.words+=[t]
						continue
					try:
						nr = int(nr)
					except:	nr = float(nr) # handling the 3.1 format for "emtpy nodes"
					if head.strip()=="_": head=-1
					else:
						try:
							head = int(head)
						except:
							head = float(head)
					egov={}
					if ":" in edeps: # the enhanced graph is used
						egov=dict([(gf.split(":")[0],gf.split(":")[-1]) for gf in edeps.split("|")])

					newf={'id':nr,'t': t,'lemma': lemma, 'tag': tag, 'xpos': xpos, 'gov':{head: rel}, 'egov':egov, 'misc': misc1+"|"+misc2}
					if "=" in features:
						mf=dict([(av.split("=")[0],av.split("=")[-1]) for av in features.split("|")])
						newf=update(mf,newf)

					tree[nr]=update(tree.get(nr,{}), newf)
					if nr>skipuntil: tree.words+=[t]

				# TODO faire ça un jour

				elif nrCells == 14:
					#mate:
					nr, t, lemma, plemma, _, tag, feat, misc, _, idgov, _, rel, _, _ = cells
					# print(plemma)
					nr = int(nr)
					newf={'id':nr,'t': t,'lemma': plemma, 'tag': tag, 'xpos': "_", 'gov':{idgov: rel} }
					tree[nr]=update(tree.get(nr,{}), newf)

				elif nrCells == 13:
					#orfeo:
					# print(cells)
					nr, t, lemma, tag, _, _, idgov, rel , _, _, time_begin, time_end, annotator = cells
					# print(plemma)
					nr = int(nr)
					newf={'id':nr,'t': t,'lemma': lemma, 'tag': tag, 'xpos': "_", 'gov':{idgov: rel} }
					tree[nr]=update(tree.get(nr,{}), newf)

			else:
				print("strange conll:",nrCells,"columns!",line)

	return tree


def conllFile2trees(path :str, encoding="utf-8"):
	trees=[]
	with open(path) as f:
		conlltext=""
		for li in f:
			li=li.strip()
			if li:
				conlltext+=li+"\n"
			else: # emptyline, sentence is finished
				tree=conll2tree(conlltext)
				# print(tree)
				trees+=[tree]
				del tree
				conlltext=""
		f.close()
		if conlltext.strip(): # last tree may not be followed by empty line
			tree=conll2tree(conlltext)
			trees+=[tree]
		return trees

def conllString2trees(conllstring, encoding="utf-8"):
	conlls = conllstring.split("\n\n")
	trees = list()
	for c in conlls:
		tree = conll2tree(c)
		trees.append(tree)
	return trees

def trees2conllFile(trees, outfile, sentencefeatures=True, columns="u"): # changed default from 10 to u!
	with open(outfile,"w") as f:
		for tree in trees:
			if columns=="u": # conllu format
				treestring = tree.conllu()
				if not sentencefeatures:
					# print(treestring)
					treestring = treestring.split("\n")
					treestring = [elt for elt in treestring if elt]
					treestring = "\n".join([elt for elt in treestring if elt[0] != "#"])+"\n"
			else:
				treestring = ""
				if sentencefeatures:
					for stftkey in sorted(tree.sentencefeatures):
						if stftkey=="_comments":
							treestring+=tree.sentencefeatures[stftkey]
						else:
							treestring+=stftkey+" = "+tree.sentencefeatures[stftkey]
				for i in sorted(tree.keys()):
					node = tree[i]
					gov = node.get("gov",{}).items()
					govid = -1
					func = "_"
					if gov:
						for govid,func in gov:
							if columns==10:
								treestring+="\t".join([str(i), node.get("t","_"), node.get("lemma",""), node.get("cat","_"), node.get("xpos","_"), "_", str(govid),func,"_","_"])+"\n"
							elif columns==14:
								lemma = node.get("lemma","_")
								if lemma == "_": lemma = node.get("t","_")
								treestring+="\t".join([str(i), node.get("t","_"), "_", "_", node.get("tag","_"), node.get("tag","_"), node.get("morph","_"), node.get("morph","_"), str(govid),str(govid),func,func,"_","_"])+"\n"
					else:
						if columns==10:
							treestring+="\t".join([str(i), node.get("t","_"), node.get("lemma",""), node.get("cat","_"), node.get("xpos","_"), "_", str(govid),func,"_","_"])+"\n"

						elif columns==14:
							lemma = node.get("lemma","_")
							if lemma == "_": lemma = node.get("t","_")
							treestring+="\t".join([str(i), node.get("t","_"), lemma, lemma, node.get("tag","_"), node.get("tag","_"), node.get("morph","_"), node.get("morph","_"), str(govid),str(govid),func,func,"_","_"])+"\n"
			f.write(treestring+"\n")


def sentences2emptyConllFile(infile, outfile):
	"""
	transforms a list of sentences into conll format without trees
	"""
	inf = open(infile)
	with open(outfile, "w") as outf:
		counter=0
		for line in inf:
			line=line.strip()
			if line:
				conllu_string = sentenceToEmptyConlluString(line)
				outf.write(conllu_string)
				outf.write("\n")
				counter+=1
		inf.close()
	# print(counter, "sentences")

def sentenceToEmptyConlluString(sentence):
	conllu_string = ""
	for i,word in enumerate(sentence.split()):
			conllu_string += "\t".join([str(i+1),word,word,"_","_","_","-1","_","_","_"])+"\n"
	return conllu_string

def emptyConllu(conllu):
	processed_lines = []
	for line in conllu.split("\n"):
		if not line.startswith("#"):
			rows = line.split("\t")
			for i in range(2, len(rows)):
				rows[i] = "_"
			line = "\t".join(rows)
		processed_lines.append(line)

	emptied_conllu = "\n".join(processed_lines)
	return emptied_conllu

def changeMetaField(conllu, target_field, new_value):
	processed_lines = []
	for line in conllu.split("\n"):
		if line.startswith("#"):
			field = line.split(" = ")[0].strip("# ")
			if field == target_field:
				line = "# " + target_field + " = " + str(new_value)
	
		processed_lines.append(line)
	
	processed_conllu = "\n".join(processed_lines)
	return processed_conllu


def conllFolder2trees(folder):
	fichiers = glob.glob(folder+"*.conllu")
	trees = list()
	for fichier in fichiers:
		trees.extend(conllFile2trees(fichier))
	return trees

def trees2transcription(trees, outfile, delim=" "):
	with open(outfile, "w") as outf:
		for t in trees:
			for node in t.values():
				outf.write(node["t"]+delim)
			outf.write("\n")

def get_weight_kids(tree, node, weights):
	"""
	called inside optimal_linearization(), recursive

	@args:
	- Tree()
	- node (root node for the first call)
	- dict() (empty for initialization)

	recursive function, returns a dictionary with the weights (number of descendants, direct and indirect) of each node
	"""
	kids = node.get("kids").keys()
	if kids:
		weights[node["id"]] = 0
		for k in kids:
			weights[node["id"]] +=1
			weights = get_weight_kids(tree, tree[k], weights)
			# print(node["id"], "current child", k, "weight of child", weights[k], "new node weight", weights[node["id"]]+weights[k])
			weights[node["id"]] += weights[k]
	else:
		weights[node["id"]] = 0
		return weights
	return weights

def unpunctATree(tree):
	new_tree = copy.deepcopy(tree)
	changes = dict()

	for i,node in tree.items():
		if new_tree.get(i):

			# we will replace the node by the following node until we reach the end of the tree
			if new_tree[i]["tag"] == "PUNCT":
				# print(new_tree[i])
				j = i
				while j < len(new_tree):
					new_tree[j] = new_tree[j+1]

					# record those changes in a mapping dict
					changes[j+1] = j
					j+=1
				
				# get rid of last node which has been doubled
				new_tree.pop(j)
			# else:
				
			# 	print(new_tree[i])
		else:
			if new_tree.get(changes.get(i)):
				print(node)

	# change numerotation for governors when it is needed
	for i,node in new_tree.items():
		idgov, rel = list(node["gov"].items())[0]
		node["gov"] = {changes.get(idgov, idgov):rel}
	return new_tree


def unpunctATree_2(tree):
	new_tree = copy.deepcopy(tree)
	removed = []

	ids_punct = [k for k in new_tree if new_tree[k]["tag"]=="PUNCT"]
	for id in ids_punct:
		del new_tree[id]
	best_tree = list()
	for k in new_tree:
		my_id = new_tree[k]["id"]
		idgov, rel = list(new_tree[k]["gov"].items())[0]
		new_idgov = idgov
		for id in ids_punct:
			if k > id:
				my_id -= 1
			if idgov > id:
				new_idgov -= 1
		new_tree[k]["id"] = my_id
		new_tree[k]["gov"] = {new_idgov:rel}
		best_tree.append(new_tree[k])
	t = Tree(dict([(elt["id"],elt) for elt in best_tree]))
	return t


if __name__ == "__main__":
	conll = """1	彭拿路	彭拿路	PROPN	NNP	_	2	nsubj	_	SpaceAfter=No
2	以	以	VERB	VV	Voice=Cau	25	dep	_	SpaceAfter=No
3	自己	自己	PRON	PRD	_	5	nsubj	_	SpaceAfter=No
4	所	所	ADV	RB	_	5	mark	_	SpaceAfter=No
5	在	在	VERB	VV	_	7	acl:relcl	_	SpaceAfter=No
6	的	的	PART	DEC	_	5	mark:relcl	_	SpaceAfter=No
7	地區	地區	NOUN	NN	_	9	nsubj	_	SpaceAfter=No
8	為	為	AUX	VC	_	9	cop	_	SpaceAfter=No
9	名	名	NOUN	NN	_	2	ccomp	_	SpaceAfter=No
10	,	,	PUNCT	,	_	25	punct	_	SpaceAfter=No
11	而	而	ADV	RB	_	25	mark	_	SpaceAfter=No
12	該區	該區	NOUN	NN	_	14	det	_	SpaceAfter=No
13	的	的	PART	DEC	Case=Gen	12	case:dec	_	SpaceAfter=No
14	名字	名字	NOUN	NN	_	25	nsubj	_	SpaceAfter=No
15	則	則	ADV	RB	_	16	mark	_	SpaceAfter=No
16	取	取	VERB	VV	_	25	acl	_	SpaceAfter=No
17	自	自	VERB	VV	_	16	mark	_	SpaceAfter=No
18	義大利	義大利	PROPN	NNP	_	19	nmod	_	SpaceAfter=No
19	皮內羅洛	皮內羅洛	PROPN	NNP	_	16	obj	_	SpaceAfter=No
20	(	(	PUNCT	(	_	21	punct	_	SpaceAfter=No
21	Pinerolo	Pinerolo	X	FW	_	19	appos	_	SpaceAfter=No
22	)	)	PUNCT	)	_	21	punct	_	SpaceAfter=No
23	,	,	PUNCT	,	_	25	punct	_	SpaceAfter=No
24	從此	從此	ADV	RB	_	25	advmod	_	SpaceAfter=No
25	成	成	VERB	VV	_	0	root	_	SpaceAfter=No
26	為	為	VERB	VC	_	25	mark	_	SpaceAfter=No
27	蒙得維	蒙得維	PROPN	NNP	_	31	det	_	SpaceAfter=No
28	的	的	PART	DEC	Case=Gen	27	case:dec	_	SpaceAfter=No
29	亞	亞	PART	PFA	_	30	case:pref	_	SpaceAfter=No
30	工人	工人	NOUN	NN	_	31	nmod	_	SpaceAfter=No
31	階級	階級	NOUN	NN	_	33	det	_	SpaceAfter=No
32	的	的	PART	DEC	Case=Gen	31	case:dec	_	SpaceAfter=No
33	代表	代表	NOUN	NN	_	25	obj	_	SpaceAfter=No
34	.	.	PUNCT	.	_	25	punct	_	SpaceAfter=No
"""

	t = unpunctATree_2(conll2tree(conll))
	print(t.conllu())
	pass