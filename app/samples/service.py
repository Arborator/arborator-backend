import os
import re
from typing import List, Literal, Dict
from datetime import datetime
from collections import Counter

from conllup.conllup import sentenceConllToJson, readConlluFile, writeConlluFile
from flask import abort
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

from app import db
from app.config import Config
from app.user.model import User
from app.projects.service import ProjectService
from app.utils.grew_utils import GrewService
from app.github.service import GithubCommitStatusService, GithubSynchronizationService, GithubWorkflowService

from .model import SampleExerciseLevel, SampleRole

BASE_TREE = "base_tree"


class SampleUploadService:
    @staticmethod
    def upload(
        fileobject: FileStorage,
        project_name: str,
        reextensions=None,
        existing_samples=[],
        new_username='',
        samples_without_sent_ids=[],
    ):	
        project = ProjectService.get_by_name(project_name)

        if reextensions == None:
            reextensions = re.compile(r"\.(conll(u|\d+)?|txt|tsv|csv)$")

        filename = secure_filename(fileobject.filename)
        sample_name = reextensions.sub("", filename)
        path_file = os.path.join(Config.UPLOAD_FOLDER, filename)

        fileobject.save(path_file)

        if samples_without_sent_ids and sample_name in samples_without_sent_ids: 
            add_new_sent_ids(path_file, sample_name) 
        
        check_duplicate_sent_id(path_file, sample_name)
        check_if_file_has_user_ids(path_file, sample_name)

        add_or_replace_userid(path_file, new_username)
        add_or_keep_timestamps(path_file)

        if sample_name not in existing_samples: 
            GrewService.create_sample(project_name, sample_name)

        with open(path_file, "rb") as file_to_save:
            GrewService.save_sample(project_name, sample_name, file_to_save)
            if GithubSynchronizationService.get_github_synchronized_repository(project.id):
                GithubCommitStatusService.create(project_name, sample_name)
                GithubCommitStatusService.update(project_name, sample_name)

class SampleTokenizeService:

    @staticmethod
    def tokenize(text, option, lang, project_name, sample_name, username):

        existing_samples = GrewService.get_samples(project_name)
        samples_names = [sample["name"] for sample in existing_samples]
        project = ProjectService.get_by_name(project_name)
        if sample_name not in samples_names:
            GrewService.create_sample(project_name, sample_name)
            index = 0
        else: 
            index = [sample["number_sentences"] for sample in existing_samples if sample_name == sample["name"]][0]
        conll= str()
        if lang:
            list_tokens = tokenize_plain_text(text=text, lang=lang)
            conll = conllize_plain_text(sent2toks=list_tokens,sample_name=sample_name, start=index)
        else: 
            sentences = split_sentences(text, option)
            for i in range(len(sentences)):
                if (sentences[i]):
                    index += 1
                    conll += conllize_sentence(sentences[i], sample_name, index, option)
                    

        file_name = sample_name + ".conllu"
        path_file = os.path.join(Config.UPLOAD_FOLDER, file_name)
        with open(path_file, "w") as file:
            file.write(conll)
        add_or_replace_userid(path_file, username)
        add_or_keep_timestamps(path_file)

        with open(path_file, "rb") as file_to_save:
            GrewService.save_sample(project_name, sample_name, file_to_save)
            if GithubSynchronizationService.get_github_synchronized_repository(project.id):
                GithubCommitStatusService.create(project_name, sample_name)
                GithubCommitStatusService.update(project_name, sample_name)
             
   
class SampleRoleService:
    @staticmethod
    def create(new_attrs):
        new_sample_role = SampleRole(**new_attrs)
        db.session.add(new_sample_role)
        db.session.commit()
        return new_sample_role

    @staticmethod
    def get_one(
        project_id: int,
        sample_name: str,
        user_id: int,
        role: int,
    ):
        """Get one specific user role """
        role = (
            db.session.query(SampleRole)
            .filter(SampleRole.user_id == user_id)
            .filter(SampleRole.project_id == project_id)
            .filter(SampleRole.sample_name == sample_name)
            .filter(SampleRole.role == role)
            .first()
        )

    @staticmethod
    def delete_one(
        project_id: int,
        sample_name: str,
        user_id: int,
        role: int,
    ):
        """Delete one specific user role """
        role = (
            db.session.query(SampleRole)
            .filter(SampleRole.user_id == user_id)
            .filter(SampleRole.project_id == project_id)
            .filter(SampleRole.sample_name == sample_name)
            .filter(SampleRole.role == role)
            .first()
        )
        if not role:
            return []
        db.session.delete(role)
        db.session.commit()
        return [(project_id, sample_name, user_id, role)]

    @staticmethod
    def get_by_sample_name(project_id: int, sample_name: str):
        """Get a dict of annotators and validators for a given sample"""
        roles = {}
        for r, label in SampleRole.ROLES:
            role = (
                db.session.query(User, SampleRole)
                .filter(User.id == SampleRole.user_id)
                .filter(SampleRole.project_id == project_id)
                .filter(SampleRole.sample_name == sample_name)
                .filter(SampleRole.role == r)
                .all()
            )
            roles[label] = [{"key": a.username, "value": a.username} for a, b in role]

        return roles

    @staticmethod
    def delete_by_sample_name(project_id: int, sample_name: str):
        """Delete all access of a sample. Used after a sample deletion was asked by the user
        ... perform on grew server."""
        roles = (
            db.session.query(SampleRole)
            .filter(SampleRole.project_id == project_id)
            .filter(SampleRole.sample_name == sample_name)
            .all()
        )
        for role in roles:
            db.session.delete(role)
        db.session.commit()

        return

    # def get_annotators_by_sample_id(project_id: int, sample_id: int) -> List[str]:
    #     return


class SampleExerciseLevelService:
    @staticmethod
    def create(new_attrs) -> SampleExerciseLevel:
        new_sample_access_level = SampleExerciseLevel(**new_attrs)
        db.session.add(new_sample_access_level)
        db.session.commit()
        return new_sample_access_level

    @staticmethod
    def update(sample_exercise_level: SampleExerciseLevel, changes):
        sample_exercise_level.update(changes)
        db.session.commit()
        return sample_exercise_level

    @staticmethod
    def get_by_sample_name(project_id: int, sample_name: str) -> SampleExerciseLevel:
        sample_exercise_level = SampleExerciseLevel.query.filter_by(
            sample_name=sample_name, project_id=project_id
        ).first()
        return sample_exercise_level

    @staticmethod
    def delete_by_sample_name(project_id: int, sample_name: str):
        """Delete all access of a sample. Used after a sample deletion was asked by the user
        ... perform on grew server."""
        roles = (
            db.session.query(SampleExerciseLevel)
            .filter(SampleExerciseLevel.project_id == project_id)
            .filter(SampleExerciseLevel.sample_name == sample_name)
            .all()
        )
        for role in roles:
            db.session.delete(role)
        db.session.commit()

        return



class SampleEvaluationService:
    @staticmethod
    def evaluate_sample(sample_conlls):
        corrects = {}
        submitted = {}
        total = {"UPOS": 0, "DEPREL": 0, "HEAD": 0}
        for sentence_id, sentence_conlls in sample_conlls.items():
            teacher_conll = sentence_conlls.get("teacher")
            if teacher_conll:
                teacher_sentence_json = sentenceConllToJson(
                    teacher_conll
                )
                teacher_tree = teacher_sentence_json["treeJson"]['nodesJson']

                basetree_conll = sentence_conlls.get(BASE_TREE)
                if basetree_conll:
                    basetree_sentence_json = (
                        sentenceConllToJson(basetree_conll)
                    )
                    basetree_tree = basetree_sentence_json["treeJson"]['nodesJson']
                else:
                    basetree_tree = {}

                for token_id in teacher_tree.keys():
                    teacher_token = teacher_tree.get(token_id)
                    if teacher_token == None:
                        continue
                    basetree_token = basetree_tree.get(token_id, {})
                    for label in ["UPOS", "HEAD", "DEPREL"]:
                        if (
                            teacher_token[label] != "_"
                            and basetree_token.get(label) != teacher_token[label]
                        ):
                            total[label] += 1
            else:
                continue

            for user_id, user_conll in sentence_conlls.items():

                if user_id != "teacher":
                    if not corrects.get(user_id):
                        corrects[user_id] = {"UPOS": 0, "DEPREL": 0, "HEAD": 0}
                    if not submitted.get(user_id):
                        submitted[user_id] = {"UPOS": 0, "DEPREL": 0, "HEAD": 0}

                    user_sentence_json = sentenceConllToJson(
                        user_conll
                    )
                    user_tree = user_sentence_json["treeJson"]["nodesJson"]

                    for token_id in user_tree.keys():
                        teacher_token = teacher_tree.get(token_id)
                        if teacher_token == None:
                            continue

                        user_token = user_tree.get(token_id)
                        basetree_token = basetree_tree.get(token_id, {})

                        for label in ["UPOS", "HEAD", "DEPREL"]:
                            if (
                                teacher_token[label] != "_"
                                and basetree_token.get(label) != teacher_token[label]
                            ):
                                if user_token[label] != "_":
                                    submitted[user_id][label] += 1
                                corrects[user_id][label] += (
                                    teacher_token[label] == user_token[label]
                                )
        GRADE = 100
        evaluations = {}
        for user_id in corrects.keys():
            evaluations[user_id] = {}
            for label in ["UPOS", "HEAD", "DEPREL"]:
                if total[label] == 0:
                    score = 0
                else:
                    score = corrects[user_id][label] / total[label]

                score_on_twenty = score * GRADE
                rounded_score = int(score_on_twenty)
                evaluations[user_id][f"{label}_total"] = total[label]
                evaluations[user_id][f"{label}_submitted"] = submitted[user_id][label]
                evaluations[user_id][f"{label}_correct"] = corrects[user_id][label]
                evaluations[user_id][f"{label}_grade_on_{GRADE}"] = rounded_score

        return evaluations

    @staticmethod
    def evaluations_json_to_tsv(evaluations):
        if evaluations == {}:
            # noone works on these trees
            return ""

        list_usernames = list(evaluations.keys())
        first_username = list(evaluations.keys())[0]
        columns = list(evaluations[first_username].keys())

        evaluations_tsv = "\t".join(["usernames"] + list_usernames)

        for label in columns:
            user_tsv_line_list = [label]
            for username in list_usernames:
                user_tsv_line_list.append(str(evaluations[username][label]))
            user_tsv_line_string = "\t".join(user_tsv_line_list)
            evaluations_tsv += "\n" + user_tsv_line_string
        return evaluations_tsv


#
#
#############    Helpers Function    #############
#
#
def split_conll_string_to_conlls_list(conll_string) -> List[str]:
    conlls_strings = conll_string.split("\n\n")
    return conlls_strings
    
def readConlluFileWrapper(path_file: str, keepEmptyTrees: bool = False):
    """ read a conllu file and return a list of sentences """
    try:
        sentences_json = readConlluFile(path_file, keepEmptyTrees=keepEmptyTrees)
        return sentences_json
    except Exception as e:
        print('debug_read_conll: {}'.format(str(e)))
        abort(406, str(e))

def writeConlluFileWrapper(path_file: str, sentences_json: List[Dict]):
    """ write a conllu file from a list of sentences """
    try:
        writeConlluFile(path_file, sentences_json, overwrite=True)
    except Exception as e:
        print('debug_write_conll: {}'.format(str(e)))
        abort(406, str(e))

def add_or_keep_timestamps(path_file: str, when: Literal["now", "long_ago"] = "now"):
    """ adds a timestamp on the tree if there is not one """
    sentences_json = readConlluFileWrapper(path_file, keepEmptyTrees=True)
    timestamp_str = str(datetime.timestamp(datetime.now()) * 1000)
    if when == "long_ago":
        timestamp_str = 0
    for sentence_json in sentences_json:
        sentence_json["metaJson"]["timestamp"] = sentence_json["metaJson"].get("timestamp", timestamp_str)

    writeConlluFileWrapper(path_file, sentences_json)

def add_or_replace_userid(path_file: str, new_user_id: str):
    """ adds a userid on the tree or replace it if already has one """
    sentences_json = readConlluFileWrapper(path_file, keepEmptyTrees=True)
    for sentence_json in sentences_json:
        sentence_json["metaJson"]["user_id"] = new_user_id

    writeConlluFileWrapper(path_file, sentences_json)

def check_duplicate_sent_id(path_file: str, sample_name: str):
    sent_ids = []
    sentences_json = readConlluFileWrapper(path_file, keepEmptyTrees=True)
    for sentence_json in sentences_json:
        sent_ids.append(sentence_json["metaJson"]["sent_id"])
    sent_ids_count = Counter(sent_ids)
    for count in sent_ids_count.values():
        if count > 1:
            abort(406, "{} has duplicated sent_ids".format(sample_name))
    return
    
def check_if_file_has_user_ids(path_file: str, sample_name: str):
    sentences_json = readConlluFileWrapper(path_file, keepEmptyTrees= True)
    if any(sentence["metaJson"]["user_id"] for sentence in sentences_json if "user_id" in sentence["metaJson"].keys()):
        abort(406, "{} has sentences with user_id".format(sample_name))

def check_sentences_without_sent_ids(path_file: str, sample_name: str):
    sentences_json = readConlluFileWrapper(path_file, keepEmptyTrees=True)
    sentence_ids_number = len([sentence for sentence in sentences_json if "sent_id" in sentence["metaJson"].keys()])
    return len(sentences_json) == sentence_ids_number

def add_new_sent_ids(path_file: str, sample_name):
    """ adds sent_id for samples that don't have sent_ids"""
    index = 0
    sentences_json = readConlluFileWrapper(path_file,keepEmptyTrees= True)
    for sentence_json in sentences_json:
        index+=1
        sentence_json["metaJson"]["sent_id"] = '{}__{}'.format(sample_name, index)
    writeConlluFileWrapper(path_file, sentences_json)

###########################"tokenizer Kim's script" ###########################

re_url = re.compile(r'''(https?://|\w+@)?[\w\d\%\.]*\w\w\.\w\w[\w\d~/\%\#]*(\?[\w\d~/\%\#]+)*''', re.U+re.M+re.I)
# combinations of numbers:
re_spacenum = re.compile(r'\d+[ ,.]+[0-9 ,.]*\d+')
# regex to match escapes \number\ used for special words:
rerematch = re.compile(r'\\\d+\\')

def tokenize_plain_text( text,
              lang,
              sent_ends='.;!?\\n',
              new_sent_upper='.!?',
              char_in_word='_-',
              whole_words="aujourd'hui l'on etc. Mr. M. Nr. N° ;) ;-)",
              special_suffix="n't -je -tu -il -elle -on -nous -vous -ils -ils -elles -y -t-il -t-elle -t-ils -t-ils -t-on",
              keep_url=True, 
              combine_numbers=True, 
              sent_cut="", 
              escape = '____',
              sent_not_cut="§§§",
             ):
     """
	text: 
		Text a transformer en Conll
	sent_ends='.;!?\\n'
		These characters end a sentence backslach escapes should be double escaped like \\n
	new_sent_upper=".!?"
		If not empty, these characters end a sentence only if the following character is upper case, should be a subset of sent_ends
	char_in_word='_-', 
		Characters that should be treated as letters inside words
	glue_left="'~", 
		Cut token after these characters 
	glue_right="" 
		Cut token before these characters 
	whole_words="aujourd'hui l'on etc. Mr. M. Nr. N° ;) ;-)", 
		Keep these space-separated words as one tokens
	special_suffix="n't -je -tu -il -elle -on -nous -vous -ils -ils -elles -y -t-il -t-elle -t-ils -t-ils -t-on",
		Keep these space-separated suffixes as separate tokens
	keep_url=True, 
		Look for URLs and keep them together
	combine_numbers=True, 
		Spaces, commas, and points between numbers are grouped together such as 999 349
	sent_cut="", 
	 	A unique word or sequence where cutting should be done. if set, sent_ends is ignored
	escape = '____', 
		No need to change this. should be letters (\w) used to escape internally. 
		Should not appear anywhere in the text
	sent_not_cut="§§§", # symbols that have been placed after the potential sent_ends that should not end the sentence. 
		This should be a unique symbol not appearing anywhere naturally in the text as it will be removed from the text.
		for example use sent_not_cut="§§§"
	"""
     whole_words = whole_words.strip().split()
     special_suffix = special_suffix.strip()
     num_dot = (escape+'{}'+escape).format('NUMBERDOT')
     space_after_esc = (escape+'{}'+escape).format('NOSPACEAFTER')
     if lang == 'fr':
        glue_left="'~"
        glue_right=""
     else:
        glue_left=""
        glue_right="'"
     ind = 0
     ntext = text
     for word in whole_words: 
        ntext = ntext.replace(word,'\\{ind}\\'.format(ind=ind))
        ind +=1
     if special_suffix:
        respecial_suffix = re.compile(r'({})\b'.format('|'.join(special_suffix.split())))
        for m in respecial_suffix.finditer(ntext):
             ntext = ntext.replace(m.group(0),'\\{ind}\\'.format(ind=ind))
             whole_words += [m.group(0)]
             ind +=1
     if keep_url:
        for murl in re_url.finditer(ntext):
            ntext = ntext.replace(murl.group(0),'\\{ind}\\'.format(ind=ind))
            whole_words += [murl.group(0)]
            ind +=1
     if combine_numbers:
        for mnum in re_spacenum.finditer(ntext):
            ntext = ntext.replace(mnum.group(0),'\\{ind}\\'.format(ind=ind))
            whole_words += [mnum.group(0)]
            ind +=1

	# replace "the 2. guy" by "the 2___NUMDOT___ guy":
     re_num_dot = re.compile(r'\b(\d+)\.(?! [0-9A-ZÀÈÌÒÙÁÉÍÓÚÝÂÊÎÔÛÄËÏÖÜÃÑÕÆÅÐÇØ])') # num followed by . not followed by upper case
     ntext = re_num_dot.sub(r'\1'+num_dot, ntext)
	# now we split into sentences:
     if sent_cut: 
        sents = ntext.split(sent_cut)
     else:
        if new_sent_upper:
            sent_ends_nopoint = re.sub(r'[{new_sent_upper}]+'.format(new_sent_upper=new_sent_upper),'', sent_ends)
            if sent_not_cut:
                re_sent_bounds = re.compile(
					'(([{sent_ends_nopoint}]+(?!{sent_not_cut})\s*)|([{sent_ends}]+(?!{sent_not_cut})\s*(?=[0-9\\\A-ZÀÈÌÒÙÁÉÍÓÚÝÂÊÎÔÛÄËÏÖÜÃÑÕÆÅÐÇØ])))'.format(
								sent_ends_nopoint=sent_ends_nopoint, 
								sent_ends=new_sent_upper.replace('.','\.'),
								sent_not_cut=sent_not_cut), re.U+re.M)
            else:
                re_sent_bounds = re.compile(
					'(([{sent_ends_nopoint}]+\s*)|([{sent_ends}]+\s*(?=[0-9\\\A-ZÀÈÌÒÙÁÉÍÓÚÝÂÊÎÔÛÄËÏÖÜÃÑÕÆÅÐÇØ])))'.format(
								sent_ends_nopoint=sent_ends_nopoint, 
								sent_ends=new_sent_upper.replace('.','\.'),
								sent_not_cut=sent_not_cut), re.U+re.M)
        else:
            if sent_not_cut:
                re_sent_bounds = re.compile(
					'([{sent_ends}](?!{sent_not_cut})+\s*)'.format(sent_ends=sent_ends, 
						    sent_not_cut=sent_not_cut), re.U+re.M)
            else:
                re_sent_bounds = re.compile(
					'([{sent_ends}]+\s*)'.format(sent_ends=sent_ends), re.U+re.M)
        doubsents = re_sent_bounds.split(ntext)+['']
        sents = []
        for i in range(0, len(doubsents), 2):
            if doubsents[i] and doubsents[i+1] is not None:
                sents += [(doubsents[i].replace(sent_not_cut,'') + (doubsents[i+1] if i+1 < len(doubsents) else '')).strip()]
	
	### now we got the sents list, making the actual tokens
     retok = re.compile("(?!(\\\\d+\\\)|([\\\{} ]+))(\W+)(?!\d)".format(re.escape((char_in_word+glue_left+glue_right).replace('-','\-'))))
     reglue_left = re.compile(r'([{}])'.format(glue_left)) if glue_left else None
     reglue_right = re.compile(r'([{}])'.format(glue_right)) if glue_right else None
     stoks = {}
     def simplerematchreplace(matchobj): # used to reconstruct the sentence
        return whole_words[int(matchobj.group(0)[1:-1])]
     def rematchreplace(matchobj): # used to build the correct tokens
        if special_suffix and respecial_suffix.match(whole_words[int(matchobj.group(0)[1:-1])]):
            return space_after_esc+whole_words[int(matchobj.group(0)[1:-1])]
        return whole_words[int(matchobj.group(0)[1:-1])]
     for si,s in enumerate(sents):
        rs = rerematch.sub(simplerematchreplace,s.replace(num_dot,'.'))
        if glue_left: s = reglue_left.sub(r'\1 ', s)
        if glue_right: s = reglue_right.sub(r' \1', s)
        s = retok.sub(r'{}\3 '.format(space_after_esc), s) # adding the additional spaces
        toks = []
        spaceafters = []
        for t in s.split():
            t = t.replace(num_dot,'.')
            ts = rerematch.sub(rematchreplace,t) if rerematch.search(t) else t
            tsl = [tt for tt in ts.split(space_after_esc) if tt] 
            toks+= tsl
            spaceafters += [ii==len(tsl)-1 for ii,tt in enumerate(tsl)]
        stoks[(si,rs)] = list(zip(toks,spaceafters)) # 'si' makes keys unique and allows duplicate sentences
     return stoks

def conllize_plain_text(sent2toks, sample_name, start):
    conlls=[]
    for (si,s),toksas in sent2toks.items():
        conllines=[
            '# sent_id = {id}__{ind}'.format(id=sample_name,ind=start+1),
            '# text = {s}'.format(s=s)
        ]
        for i,(tok,sa) in enumerate(toksas):
            li = '{ind}\t{tok}\t_\t_\t_\t_\t_\t_\t_\t{spac}\t'.format(ind=i+1,tok=tok,spac='_' if sa else 'SpaceAfter=No')
            conllines+=[li]
        conlls+=['\n'.join(conllines)]
        start+=1
    return '\n\n'.join(conlls)+'\n'

def split_sentences(text, option):
    if option == 'horizontal':
        return text.split("\n")
    else:
        sentences = []
        for sentence in text.split('\n\n'):
            sentences.append(sentence)
        return sentences

def conllize_sentence(sentence_tokens, sample_name, index, option):
    sent_id = '# sent_id = {}__{}\n'.format(sample_name, index)
    text = '# text = '
    sentence = str()
    conll = str()
    i = 1
    delimiter = " " if option == 'horizontal' else "\n" 
    for token in sentence_tokens.rstrip().split(delimiter):
        text += "{} ".format(token)
        sentence += '{}\t{}\t_\t_\t_\t_\t_\t_\t_\t_\t\n'.format(i,token)
        i += 1
    conll += sent_id
    conll += text +"\n"
    conll += sentence + "\n"
    return conll
