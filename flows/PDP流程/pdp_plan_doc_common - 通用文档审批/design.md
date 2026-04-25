# pdp_plan_doc_common 通用文档审批

## 基本信息

| 字段 | 值 |
|------|-----|
| 流程Key | `pdp_plan_doc_common` |
| 所属模块 | PDP |
| 表单类型 | 自定义表单 |
| 发起页面 | `/crm/fea/create`（⚠️ 待确认） |
| 查看页面 | `/crm/fea/get`（⚠️ 待确认） |
| businessKey | `planDefMainId` |

## 流程节点

```
开始 → [执行]（流程变量指定人）→ [计划负责人]（流程变量指定人）→ 结束
```

| 节点 | 类型 | 审批人策略 | 变量名 | 说明 |
|------|------|-----------|--------|------|
| 执行 | UserTask | `60` 流程表达式 | `${executorUserId}` | 计划执行人，发起时传入 |
| 计划负责人 | UserTask | `60` 流程表达式 | `${PdpPlanChargeUser}` | 计划负责人确认，发起时传入 |

## 流程变量

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `executorUserId` | Long | 执行人用户ID |
| `PdpPlanChargeUser` | Long | 计划负责人用户ID |

## 后端监听

### 业务侧（pdp-server）

继承 `AbstractPlanProcessStatusListener`，对应 Listener 类：`PlanDocCommonProcessStatusListener`

```java
@RestController
@FeignClient(name = ApiConstants.NAME)
public class PlanDocCommonProcessStatusListener
        extends AbstractPlanProcessStatusListener {

    @Override
    protected String getProcessDefinitionKey() {
        return "pdp_plan_doc_common";
    }
}
```

状态处理逻辑：
- APPROVE → `plan.status = 5`（已完成），设置 `completedTime`
- REJECT / CANCEL → 仅更新 `auditStatus`

## 设计要点

- 文档类通用模板，结构与 `pdp_plan_common` 完全相同
- 使用独立 Listener（`PlanDocCommonProcessStatusListener`），不依赖 `PlanDefMainProcessStatusListener`
- 审批人完全由流程变量决定，两节点：执行 → 负责人确认
