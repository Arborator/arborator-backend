import json

from flask import abort
from conllup.conllup import sentenceConllToJson, sentenceJsonToConll

from app import db

from app.utils.grew_utils import grew_request
from .model import UserTags 

class TagService: 

    @staticmethod
    def add_new_tags(project_name, sample_name, tags, conll):
        
        tags_value = ''
        new_tags = ', '.join(tags)

        sentence_json = sentenceConllToJson(conll)
        if "tags" in sentence_json["metaJson"].keys():
            existing_tags = sentence_json["metaJson"]["tags"]
            tags_value = f"{existing_tags}, {new_tags}"
        else:
            tags_value = new_tags
       
        sentence_json["metaJson"]["tags"] = tags_value
        user_id = sentence_json["metaJson"]["user_id"]
        
        conll = sentenceJsonToConll(sentence_json)
        grew_request('saveGraph', data= {
            "project_id": project_name,
            "sample_id": sample_name, 
            "user_id": user_id,
            "conll_graph": conll
        })
        return sentence_json["metaJson"]

    @staticmethod
    def remove_tag(project_name, sample_name, tag, conll):

        sentence_json = sentenceConllToJson(conll)
        user_id = sentence_json["metaJson"]["user_id"]
        
        if "tags" in sentence_json["metaJson"].keys():
            
            existing_tags = list(map(lambda tag: tag.strip(), sentence_json["metaJson"]["tags"].split(",")))
            existing_tags.remove(tag.strip())
            tags_value = ', '.join(existing_tags)

            if tags_value:
                sentence_json["metaJson"]["tags"] = tags_value
            else: 
                sentence_json["metaJson"].pop("tags")

            conll = sentenceJsonToConll(sentence_json)
            grew_request('saveGraph', data={
                "project_id": project_name,
                "sample_id": sample_name,
                "user_id": user_id,
                "conll_graph": conll
            })
            return sentence_json["metaJson"]
        else: 
            abort(406, "This sentence doesn't contain tags")


class UserTagsService:

    @staticmethod
    def get_by_user_id(user_id) -> UserTags:
        return UserTags.query.filter(UserTags.user_id == user_id).first()
    
    @staticmethod
    def create_or_update(new_attrs) -> UserTags:
        user_tags_entry = UserTagsService.get_by_user_id(new_attrs.get("user_id"))
        if user_tags_entry:
            existing_tags = user_tags_entry.tags
            new_attrs["tags"] = existing_tags + new_attrs.get("tags")
            user_tags_entry.update(new_attrs)
        else:    
            user_tags_entry = UserTags(**new_attrs)
            db.session.add(user_tags_entry)
        
        db.session.commit()
        return user_tags_entry
    
    @staticmethod
    def delete_tag(user_id, tag):
        user_tags_entry = UserTagsService.get_by_user_id(user_id)
        if user_tags_entry.tags: 
            existing_tags = list(user_tags_entry.tags)
            existing_tags.remove(tag)
            if existing_tags: 
                user_tags_entry.update({"tags": existing_tags })
            else:    
                db.session.delete(user_tags_entry)
        db.session.commit()
        
    
    
        


        



        

