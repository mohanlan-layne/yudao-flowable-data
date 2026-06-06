# PA：建分支 + 把 UAT 缺失分类同步进 PROD 数据库

1. 建工作分支：git fetch origin; git checkout -B uat2prod-promote origin/master。
2. 写脚本 scripts/sync_categories.py（pymysql），把 UAT 缺失分类同步进 PROD，保留原 id：
   - DB：host=192.168.1.190 port=3306 user=yudao password=Yudao@2025；源库 yudao_uat，目标库 yudao_prod，表 bpm_category。
   - 取 yudao_uat.bpm_category 中 id IN (125,126,127,128,129,130,131,132) 且 deleted=0 的 8 行（SELECT *）。
   - 对目标库幂等插入：该 id 在 yudao_prod 已存在则跳过（不覆盖），不存在才 INSERT（带原 id 和所有列）。
   - 支持 --dry-run 只打印不写库；默认先自动 dry-run 预览，再真执行。
   - 真执行后校验：SELECT id,code,name,deleted FROM yudao_prod.bpm_category WHERE id IN (125..132)，确认 8 个都在、与 UAT 一致、deleted=0。
   - 铁律：只 INSERT 这 8 个 id；绝不 UPDATE/DELETE PROD 任何行；绝不动 bpm_category 以外任何表。
3. 提交：git add scripts/sync_categories.py specs/PA-setup-db.md specs/PB-promote-one.md specs/PC-merge.md; git commit -m "晋级-建分支+PROD同步缺失分类id125到132"; git push -u origin uat2prod-promote。
