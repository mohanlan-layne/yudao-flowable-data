# pdp_plan_doc_ 系列流程 Listener 设计

## 背景

`pdp_plan_doc_` 前缀的文档类计划流程，需要独立的 Listener 类，不使用 `PlanDefMainProcessStatusListener`（它只捕获所有 `pdp_plan_` 前缀的流程，但不区分文档类和普通计划类）。

## 架构

继承 `AbstractPlanProcessStatusListener`，覆写 `getProcessDefinitionKey()` 返回精确的流程 key。

```java
// 示例：DFM审核 Listener
@RestController
@FeignClient(name = ApiConstants.NAME)
public class PlanDocDfmProcessStatusListener
        extends AbstractPlanProcessStatusListener {

    @Override
    protected String getProcessDefinitionKey() {
        return "pdp_plan_doc_dfm";
    }

    // 如果需要额外业务逻辑，覆写 onProcessCompleted()
    // @Override
    // protected void onProcessCompleted(...) { ... }
}
```

## 各文档流程对应 Listener 类

| 流程Key | Listener 类名 | 说明 |
|---------|--------------|------|
| `pdp_plan_doc_dfm` | `PlanDocDfmProcessStatusListener` | DFM审核 |
| `pdp_plan_doc_pqa` | `PlanDocPqaProcessStatusListener` | PQA审核 |
| `pdp_plan_doc_pqe` | `PlanDocPqeProcessStatusListener` | PQE审核 |
| `pdp_plan_doc_assembly` | `PlanDocAssemblyProcessStatusListener` | 装配审核 |
| `pdp_plan_doc_purchase` | `PlanDocPurchaseProcessStatusListener` | 采购审核 |
| `pdp_plan_doc_quality` | `PlanDocQualityProcessStatusListener` | 品质审核（文档）|
| `pdp_plan_doc_spare_parts` | `PlanDocSparePartsProcessStatusListener` | 备品申请 |
| `pdp_plan_doc_proposal_confirm` | `PlanDocProposalConfirmProcessStatusListener` | 方案确认 |

## 注意事项

- 每个 Listener 都需要 `@RestController` + `@FeignClient(name = ApiConstants.NAME)` 注解（参考 README.md 中的模式）
- `getProcessDefinitionKey()` 返回精确 key（不是前缀），父类会用 `startsWith` 或 `equals` 匹配
- 如无额外业务逻辑，只需覆写 `getProcessDefinitionKey()` 即可，其余复用父类
- `businessKey` 约定：= `planDefMainId`（Long），父类已处理
- 多租户：父类已通过 `TenantUtils` 处理异步场景下的租户上下文

## 父类 AbstractPlanProcessStatusListener 关键逻辑

- APPROVE → 更新 plan.status = 5（已完成），completedTime = now()
- REJECT / CANCEL → 仅更新 auditStatus
- `onProcessCompleted()` 是供子类扩展的钩子方法（空实现）
