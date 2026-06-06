# PB：单流程晋级（本任务只处理 1 个流程）

本任务的流程 key 在任务正文给出。先 git checkout uat2prod-promote。
**全程把命令输出重定向到日志，只看退出码和最后几行，绝不逐行读输出、绝不 review 大 diff。**

设 KEY 为本任务的流程 key，依次执行：

1. 刷新该流程 UAT 数据（增量、安静）：
   python3 scripts/export.py --env uat "$KEY" > /tmp/e.log 2>&1; echo rc=$?; tail -2 /tmp/e.log
   退出码非 0 则停止并报错。

2. 复制 now 到 prod：
   D=$(find uat -maxdepth 1 -type d -name "$KEY - *" | head -1)
   B=$(basename "$D")
   mkdir -p "prod/$B"; rm -rf "prod/$B/now"; cp -r "$D/now" "prod/$B/now"

3. dry-run 预览（单流程，输出短）：
   python3 scripts/import.py --env prod --dry-run "$KEY"
   确认是 create 或 update、category 正常解析、无报错。

4. 真推（只更新草稿，绝不部署）：
   python3 scripts/import.py --env prod "$KEY" > /tmp/i.log 2>&1; echo rc=$?; tail -2 /tmp/i.log
   退出码非 0 则停止并报错。

5. 提交（直接 add，不要对数据文件做 git diff）：
   git add uat prod; git commit -m "晋级-$KEY"; git push origin uat2prod-promote

铁律：只处理这一个 KEY；只 import，绝不部署。
