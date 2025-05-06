import os
import re
from typing import List, Literal, Dict
from datetime import datetime
from collections import Counter

from conllup.conllup import sentenceConllToJson, readConlluFile, sentenceJsonToConll
from flask import abort
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

from app import db
from app.config import Config
from app.projects.service import ProjectService
from app.utils.grew_utils import GrewService
from app.github.service import GithubCommitStatusService, GithubRepositoryService

from .model import SampleBlindAnnotationLevel

BASE_TREE = "base_tree"


class SampleUploadService:
    @staticmethod
    def upload(
        fileobject: FileStorage,
        project_name: str,
        filename, 
        sample_name,
        rtl: bool,
        existing_samples=[],
        new_username='',
        samples_without_sent_ids=[],
    ):	
        """uplaod new sample

        Args:
            fileobject (FileStorage): 
            project_name (str):
            filename (str): 
            sample_name (str): filename without the extension
            rtl (bool): _description_
            existing_samples (list[str]): existing sample
            new_username (str): the custom username used of the uploaded trees, or the same as the username
            samples_without_sent_ids (list[str]): list of samples that doesn't contain sent_ids Defaults to [].
        """
        project = ProjectService.get_by_name(project_name)
        path_file = os.path.join(Config.UPLOAD_FOLDER, filename)

        fileobject.save(path_file)

        if samples_without_sent_ids and sample_name in samples_without_sent_ids: 
            add_new_sent_ids(path_file, sample_name) 
        
        check_duplicate_sent_id(path_file, sample_name)
        check_if_file_has_user_ids(path_file, sample_name)

        add_or_replace_userid(path_file, new_username)
        add_or_keep_timestamps(path_file)
        
        if rtl == True:
            add_rtl_meta_data(path_file)

        if sample_name not in existing_samples: 
            GrewService.create_samples(project_name, [sample_name])

        with open(path_file, "rb") as file_to_save:
            GrewService.save_sample(project_name, sample_name, file_to_save)
            if GithubRepositoryService.get_by_project_id(project.id):
                GithubCommitStatusService.create(project.id, sample_name)
                if new_username == 'validated':
                    GithubCommitStatusService.update_changes(project.id, sample_name)
        
        os.remove(path_file)

class SampleTokenizeService:

    @staticmethod
    def tokenize(text, option, lang, project_name, sample_name, username, rtl):
        """tokenize and upload the tokenized text

        Args:
            text (str) 
            option (str): horizontal | vertical | plain_text
            lang (str): if plain text we have a tokenizer for french or english
            project_name (str)
            sample_name (str)
            username (str)
            rtl (bool): right to left script
        """
        existing_samples = GrewService.get_samples(project_name)
        samples_names = [sample["name"] for sample in existing_samples]
        project = ProjectService.get_by_name(project_name)
        if sample_name not in samples_names:
            GrewService.create_samples(project_name, [sample_name])
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
        
        if rtl == True:
            add_rtl_meta_data(path_file)

        with open(path_file, "rb") as file_to_save:
            GrewService.save_sample(project_name, sample_name, file_to_save)
            if GithubRepositoryService.get_by_project_id(project.id):
                GithubCommitStatusService.create(project.id, sample_name)
                if username == "validated":
                    GithubCommitStatusService.update_changes(project.id, sample_name)
        
        os.remove(path_file)    

class SampleBlindAnnotationLevelService:
    
    """class that deals with blind annotatio level entity"""
    @staticmethod
    def create(new_attrs) -> SampleBlindAnnotationLevel:
        """create new blind annotation level entity

        Args:
            new_attrs (dict)

        Returns:
            SampleBlindAnnotationLevel
        """
        new_blind_annotation_level = SampleBlindAnnotationLevel(**new_attrs)
        db.session.add(new_blind_annotation_level)
        db.session.commit()
        return new_blind_annotation_level

    @staticmethod
    def update(blind_annotation_level: SampleBlindAnnotationLevel, changes):
        """update blind annotation level

        Args:
            blind_annotation_level (SampleBlindAnnotationLevel)
            changes (dict(changes))

        Returns:
           updated blind annotation level
        """
        blind_annotation_level.update(changes)
        db.session.commit()
        return blind_annotation_level

    @staticmethod
    def get_by_sample_name(project_id: int, sample_name: str) -> SampleBlindAnnotationLevel:
        """Get the blind annotation level by sample_name

        Args:
            project_id (int)
            sample_name (str)

        Returns:
            SampleBlindAnnotationLevel
        """
        blind_annotation_level = SampleBlindAnnotationLevel.query.filter_by(
            sample_name=sample_name, project_id=project_id
        ).first()
        return blind_annotation_level

    @staticmethod
    def delete_by_sample_name(project_id: int, sample_name: str):
        """Delete all access of a sample. Used after a sample deletion was asked by the user
        ... perform on grew server."""
        roles = (
            db.session.query(SampleBlindAnnotationLevel)
            .filter(SampleBlindAnnotationLevel.project_id == project_id)
            .filter(SampleBlindAnnotationLevel.sample_name == sample_name)
            .all()
        )
        for role in roles:
            db.session.delete(role)
        db.session.commit()

class SampleEvaluationService:
    @staticmethod
    def evaluate_sample(sample_conlls):
        """Evaluate samples

        Args:
            sample_conlls (2-levels dict sent_id -> user_id -> conll_string)

        Returns:
            evaluations (2-level dict user_id -> evaluation -> percentage)
        """
        corrects = {}
        submitted = {}
        total = {"UPOS": 0, "DEPREL": 0, "HEAD": 0}

        for sentence_id, sentence_conlls in sample_conlls.items():
            validated_tree_conll = sentence_conlls.get("validated")
            if validated_tree_conll:
                validated_tree_sentence_json = sentenceConllToJson(
                    validated_tree_conll
                )
                validated_tree = validated_tree_sentence_json["treeJson"]['nodesJson']

                basetree_conll = sentence_conlls.get(BASE_TREE)
                if basetree_conll:
                    basetree_sentence_json = (
                        sentenceConllToJson(basetree_conll)
                    )
                    basetree_tree = basetree_sentence_json["treeJson"]['nodesJson']
                else:
                    basetree_tree = {}

                for token_id in validated_tree.keys():
                    validated_tree_token = validated_tree.get(token_id)
                    if validated_tree_token == None:
                        continue
                    basetree_token = basetree_tree.get(token_id, {})
                    for label in ["UPOS", "HEAD", "DEPREL"]:
                        if (
                            validated_tree_token[label] != "_"
                            and basetree_token.get(label) != validated_tree_token[label]
                        ):
                            total[label] += 1
            else:
                continue

            for user_id, user_conll in sentence_conlls.items():

                if user_id != "validated":
                    if not corrects.get(user_id):
                        corrects[user_id] = {"UPOS": 0, "DEPREL": 0, "HEAD": 0}
                    if not submitted.get(user_id):
                        submitted[user_id] = {"UPOS": 0, "DEPREL": 0, "HEAD": 0}

                    user_sentence_json = sentenceConllToJson(
                        user_conll
                    )
                    user_tree = user_sentence_json["treeJson"]["nodesJson"]

                    for token_id in user_tree.keys():
                        validated_tree_token = validated_tree.get(token_id)
                        if validated_tree_token == None:
                            continue

                        user_token = user_tree.get(token_id)
                        basetree_token = basetree_tree.get(token_id, {})

                        for label in ["UPOS", "HEAD", "DEPREL"]:
                            if (
                                validated_tree_token[label] != "_"
                                and basetree_token.get(label) != validated_tree_token[label]
                            ):
                                if user_token[label] != "_":
                                    submitted[user_id][label] += 1
                                corrects[user_id][label] += (
                                    validated_tree_token[label] == user_token[label]
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
        """Convert eval to tsv file

        Args:
            evaluations (dict)

        Returns:
            evaluation_tsv(str)
        """
        if evaluations:
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
        else: 
            abort(400, 'There is no available trees for evaluation')

#
#
#############    Helpers Function    #############
#
#
def split_conll_string_to_conlls_list(conll_string) -> List[str]: 
    """Split conll to list of strings 

    Args:
        conll_string (str)

    Returns:
        List[str]: list of sentences
    """
    conlls_strings = conll_string.split("\n\n")
    return conlls_strings
    
def read_conllu_file_wrapper(path_file: str, keepEmptyTrees: bool = False):
    """ read a conllu file and return a list of sentences in json format """
    try:
        sentences_json = readConlluFile(path_file, keepEmptyTrees=keepEmptyTrees)
        return sentences_json
    except Exception as e:
        print('debug_read_conll: {}'.format(str(e)))
        abort(406, str(e))

def write_conllu_file_wrapper(path_file: str, sentences_json: List[Dict]):
    """ write a conllu file from a list of sentences sentences in json format """
    
    with open(path_file, "w", encoding="utf-8") as outfile:
        for sentence_json in sentences_json:
            sentence_conll = sentenceJsonToConll(sentence_json)
            outfile.write(sentence_conll + "\n")

def add_or_keep_timestamps(path_file: str, when: Literal["now", "long_ago"] = "now"):
    """ adds a timestamp on the tree if there is not one """
    sentences_json = read_conllu_file_wrapper(path_file, keepEmptyTrees=True)
    timestamp_str = str(datetime.timestamp(datetime.now()) * 1000)
    if when == "long_ago":
        timestamp_str = 0
    for sentence_json in sentences_json:
        sentence_json["metaJson"]["timestamp"] = sentence_json["metaJson"].get("timestamp", timestamp_str)

    write_conllu_file_wrapper(path_file, sentences_json)

def add_or_replace_userid(path_file: str, new_user_id: str):
    """ adds a userid on the tree or replace it if already has one """
    sentences_json = read_conllu_file_wrapper(path_file, keepEmptyTrees=True)
    for sentence_json in sentences_json:
        sentence_json["metaJson"]["user_id"] = new_user_id

    write_conllu_file_wrapper(path_file, sentences_json)
    
def add_rtl_meta_data(path_file: str):
    """Add metadata rtl to the sentences in order to display dependency tree in rtl mode"""
    sentences_json = read_conllu_file_wrapper(path_file, keepEmptyTrees=True)
    for sentence_json in sentences_json:
        sentence_json["metaJson"]["rtl"] = "yes"   
    write_conllu_file_wrapper(path_file, sentences_json)

def check_duplicate_sent_id(path_file: str, sample_name: str):
    """Check if there is duplicated sent_id in the sample"""
    sent_ids = []
    sentences_json = read_conllu_file_wrapper(path_file, keepEmptyTrees=True)
    for sentence_json in sentences_json:
        if "sent_id" in sentence_json["metaJson"].keys():
            sent_ids.append(sentence_json["metaJson"]["sent_id"])
    sent_ids_count = Counter(sent_ids)
    for count in sent_ids_count.values():
        if count > 1:
            abort(406, "{} has duplicated sent_ids".format(sample_name))
    
def check_if_file_has_user_ids(path_file: str, sample_name: str):
    """check if in the file there is sentences with user_id"""
    sentences_json = read_conllu_file_wrapper(path_file, keepEmptyTrees= True)
    if any(sentence["metaJson"]["user_id"] for sentence in sentences_json if "user_id" in sentence["metaJson"].keys()):
        abort(406, "{} has sentences with user_id".format(sample_name))

def check_sentences_without_sent_ids(path_file: str):
    """check if there is sentences in the sample without sent_id"""
    sentences_json = read_conllu_file_wrapper(path_file, keepEmptyTrees=True)
    sentence_ids_number = len([sentence for sentence in sentences_json if "sent_id" in sentence["metaJson"].keys()])
    return len(sentences_json) == sentence_ids_number

def add_new_sent_ids(path_file: str, sample_name):
    """ adds sent_id for samples that don't have sent_ids"""
    index = 0
    sentences_json = read_conllu_file_wrapper(path_file,keepEmptyTrees= True)
    for sentence_json in sentences_json:
        index+=1
        sentence_json["metaJson"]["sent_id"] = '{}__{}'.format(sample_name, index)
    write_conllu_file_wrapper(path_file, sentences_json)
    

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
    sentence_tokens = sentence_tokens.replace("\t", ' ')
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
