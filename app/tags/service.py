from conllup.conllup import sentenceConllToJson, sentenceJsonToConll
from app.utils.grew_utils import grew_request

class TagService: 

    def add_new_tags(project_name, sample_name, tags, conll):
        
        tags_value = ''
        new_tags = ', '.join(tags)

        sentence_json = sentenceConllToJson(conll)
        if "tags" in sentence_json["metaJson"].keys():
            existing_tags = sentence_json["metaJson"]["tags"]
            tags_value = f"{existing_tags}, {new_tags}"
        else:
            tags_value = new_tags
        print(tags_value)
        sentence_json["metaJson"]["tags"] = tags_value
        user_id = sentence_json["metaJson"]["user_id"]
        
        conll = sentenceJsonToConll(sentence_json)
        grew_request('saveGraph', data= {
            "project_id": project_name,
            "sample_id": sample_name, 
            "user_id": user_id,
            "conll_graph": conll
        })



        


        



        

