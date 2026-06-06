# PC：合并 uat2prod-promote 到 master

git fetch origin; git checkout master; git reset --hard origin/master; git merge --ff-only uat2prod-promote; git push origin master。
确认 master 含本次全部晋级提交、scripts/sync_categories.py 在、prod/ 已更新。ff-only 失败则停止报告，不强推。
