#!/bin/sh

uri="$1"
repo="$2"
branch="$3"
dir="$4"

git clone -b $branch -n --depth=1 --filter=tree:0 "$uri/$repo.git"
cd $repo
git sparse-checkout set --no-cone $dir
git checkout
cd ..
