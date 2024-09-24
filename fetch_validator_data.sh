#!/bin/bash 

parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )

cd "$parent_path"

cd "app/utils/ud_validator/"

curl -L -o "repo.zip" "https://github.com/UniversalDependencies/tools/archive/refs/heads/master.zip"

unzip -q "repo.zip" -d "temp_unzip_dir"

rm -rf ./data

mv "temp_unzip_dir/tools-master/data" .

rm -rf "temp_unzip_dir" "repo.zip"
