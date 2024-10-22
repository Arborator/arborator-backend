# Information for using Klang

This is not part of the common Arborator-Grew annotation tool.

The goal of Klang is to crowdsource transcription corrections of spoken texts and to gather information about a large number of sound samples.

It allows
- correcting the transcription by listening to the sound
- adjugating multiple transcriptions
- visualize the sentence segmentation to detect overly long segments
- collecting meta-informations such as sound quality and sample name proposals
- viewing and downloading information on the annotators' activity
- re-exporting the selected transcription into sentence segmented conllu.

It has mainly been used for the ParisStories corpus collection as a preliminary stage to create the [ParisStories Universal Dependencies treebank](https://universaldependencies.org/treebanks/fr_parisstories/).
for details see
> Kahane, Sylvain, Bernard Caron, Emmett Strickland, and Kim Gerdes. "Annotation guidelines of UD and SUD treebanks for spoken corpora." In Proceedings of the 20th International Workshop on Treebanks and Linguistic Theories (TLT, SyntaxFest 2021), pp. pp-35. Association for Computational Linguistics, 2021.

You cannot yet generate projects from the command line.
You need to generate (and add to the project) a folder, e.g. my_project, with the following structure

    my_project
        contains a file and a folder:
        config.json:
            {"admins": ["xxx@gmail.com", "yyy@gmail.com", "12345678","zzz@gmail.com"],
            "private":true}
        samples 

The sample folder contains the samples. Each sample consists of a folder *my_sample* and two files:
- my_sample.intervals.conll 
- my_sample.mp3

check that:
- each sample must be in a subfolder with the same name, my_sample
- the conll file must have the same name and end with intervals.conll, in your case my_sample.conll not *conllu*
- aligns must be in miliseconds
- private is set to false if you want others than admins to access the project.

## Technical information:

When running Klang, it will save the user data into *transcription.json* files that look like this for each user that worked 
    [ 
        {"accent": "native", "monodia": "dialogue", "story": "fun", "user": "anne.ff", "sound": "good", "title": "Fashion week", "transcription": [["bah", ",", "un", "soir", "apr\u00e8s", "la", ",", "hmm", ","], ["semaine", "de", "fashion", "week", ","], ["j'", "ai", "voulu", "emmener", "ma", "meilleure", "amie", "\u00e0", ",", "hm", ","], ["\u00e0", "une", ...]

The segments are preserved, only the transcription can change. Yet, the output will be clean conll by sentence borders.


