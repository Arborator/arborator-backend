# ARGS:
    # Argument 1: path to SQLlite database
    #     example: app/arborator_dev.sqlite
    # Argument 2: path to dir for png files
    #     example: ../arborator-frontend/public/images/projectimages
    # Argument 3: database rm mode
    #     either empty or "y"
    #     Just useful during tests to quickly reset the database with an old BLOB based one

if [ ! -z "$3" ]
  then
    rm $1 cp app/arborator_dev\ \(4e\ copie\).sqlite $1
fi
# echo mkdir -p $2
# echo sqlite3 $1 "SELECT writefile('$2/' || project_name || '.png', image) FROM projects WHERE image notnull;"
mkdir -p $2
sqlite3 $1 "SELECT writefile('$2/' || project_name || '.png', image) FROM projects WHERE image notnull;"
# sqlite3 app/arborator_dev.sqlite "SELECT writefile('../arborator-frontend/public/images/projectimages/' || project_name || '.png', image) FROM projects WHERE image notnull;"