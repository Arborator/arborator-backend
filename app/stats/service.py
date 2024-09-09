from conllup.conllup import sentenceConllToJson

class StatProjectService:
    
    @staticmethod
    def get_projects_tags(sample_conlls):
        tags_set = set()
        for conll in sample_conlls.values():
            for sentence in conll.values():
                sentence_json = sentenceConllToJson(sentence)
                if 'tags' in sentence_json['metaJson'].keys():
                    tags = sentence_json['metaJson']['tags']
                    tags_list = tags.split(",")
                    for tag in tags_list:
                        tags_set.add(tag.strip())
        return tags_set
                    