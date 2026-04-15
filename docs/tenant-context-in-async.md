# 多租户上下文在异步调用中的传递规范

## 背景

yudao-cloud 采用多租户架构，租户 ID 通过 `TenantContextHolder` 在**当前线程**中持有。  
一旦脱离原始请求线程（事务提交后回调、MQ 消费线程、线程池任务等），`TenantContextHolder` 即为空，导致：
- MyBatis 多租户插件报错
- Flowable 查不到对应租户的流程定义或 execution
- 跨服务 HTTP 调用目标服务无法识别租户

---

## 场景一：Spring 事务提交后回调（afterCommit）

### 典型场景

Flowable `serviceTask` 执行期间同步调用外部服务，外部服务需要在**事务提交后**再回调触发 ReceiveTask。

### 问题根因

`TransactionSynchronizationManager.afterCommit()` 回调在事务提交后执行，此时 Spring 已清理线程上下文，`TenantContextHolder.getTenantId()` 返回 `null`。

若在 `afterCommit` 内直接发起 HTTP 请求，目标服务收不到 `tenant-id` 请求头。

### 正确做法

**在 `onEvent` / `execute` 方法内（事务上下文存活时）提前捕获 `tenantId`，通过闭包传入 `afterCommit`，手动加入请求头。**

```java
@Override
public void onEvent(BpmProcessInstanceStatusEvent event) {
    String issueId = event.getBusinessKey();
    // ✅ 在事务内提前读取，afterCommit 时上下文已清空
    Long tenantId = TenantContextHolder.getTenantId();

    TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
        @Override
        public void afterCommit() {
            HttpHeaders headers = new HttpHeaders();
            if (tenantId != null) {
                headers.add("tenant-id", String.valueOf(tenantId)); // ✅ 手动注入
            }
            loadBalancedRestTemplate.postForObject(url, new HttpEntity<>(null, headers), Void.class);
        }
    });
}
```

### 反例

```java
// ❌ afterCommit 内才读，此时为 null
public void afterCommit() {
    Long tenantId = TenantContextHolder.getTenantId(); // null！
    loadBalancedRestTemplate.postForObject(url, null, Void.class); // 无 tenant-id 头
}
```

---

## 场景二：接收 HTTP 回调时的租户上下文

### 典型场景

bpm-server 通过 HTTP 回调 pdp-server 的 RPC 接口（如 `/rpc-api/pdp/review-issue/on-sub-process-completed`）。

### 问题根因

若回调方法整体被 `TenantUtils.executeIgnore()` 包裹，内部所有代码的租户上下文均为空，包括：
- MyBatis 查询
- 再次向 bpm-server 发起调用（如 `triggerReceiveTask`）

### 正确做法

**从请求头中读取 `tenant-id`，使用 `TenantUtils.execute(tenantId, ...)` 包裹，兜底使用租户 1。**

```java
@Override
public CommonResult<Boolean> onSubProcessCompleted(Long issueId, Integer bpmStatus) {
    // ✅ 从请求头获取，bpm-server 发请求时已注入
    Long tenantId = TenantContextHolder.getTenantId();
    if (tenantId == null) {
        tenantId = 1L; // 兜底
    }
    final Long finalTenantId = tenantId;
    return TenantUtils.execute(finalTenantId, () -> {
        // 业务逻辑...
    });
}
```

### 反例

```java
// ❌ executeIgnore 清空租户，导致 triggerReceiveTask 查不到 execution
return TenantUtils.executeIgnore(() -> {
    // triggerReceiveTask 在这里调用，tenant 为空，Flowable 查不到 execution
});
```

---

## 场景三：RabbitMQ 消费端

### 问题根因

框架通过 `TenantRabbitMQMessagePostProcessor` 在**发送时**自动将 `tenantId` 写入 Message Header，  
但**消费端没有自动解析 Header 并设置租户上下文的拦截器**，需手动处理。

### 正确做法

```java
@RabbitListener(queues = "your-queue")
public void handleMessage(Message amqpMessage, YourPayload payload) {
    // ✅ 手动从 Header 读取
    Object tenantIdObj = amqpMessage.getMessageProperties().getHeaders().get(HEADER_TENANT_ID);
    Long tenantId = tenantIdObj != null ? Long.parseLong(tenantIdObj.toString()) : 1L;

    TenantUtils.execute(tenantId, () -> {
        // 业务逻辑（MyBatis 操作、BPM 调用等）
    });
}
```

### 反例

```java
// ❌ 直接调用业务逻辑，无租户上下文，MyBatis 多租户插件报 MyBatisSystemException
public void handleMessage(YourPayload payload) {
    yourService.doSomething(payload);
}
```

---

## 场景四：跨模块 RPC 调用（如 pdp-server → bpm-server）

### 问题根因

使用 `TenantUtils.executeIgnore()` 包裹的代码中调用 bpm-server 接口，bpm-server 会因租户为空查不到流程定义，抛出"流程定义不存在"异常。

### 正确做法

**从业务实体中取真实 `tenantId`，使用 `TenantUtils.execute(tenantId, ...)` 包裹调用。**

```java
Long tenantId = TenantContextHolder.getTenantId();
if (tenantId == null) {
    tenantId = 1L;
}
TenantUtils.execute(tenantId, () -> processInstanceApi.createProcessInstance(userId, reqDTO));
```

---

## 总结：各场景处理方式速查

| 场景 | 租户丢失原因 | 解决方式 |
|------|-------------|---------|
| `afterCommit` 内发 HTTP | 事务提交后上下文清空 | 事务内提前捕获 `tenantId`，手动加入 HTTP Header |
| 接收 HTTP 回调 | 被 `executeIgnore` 包裹 | 改用 `TenantUtils.execute(tenantId, ...)` + 兜底 1 |
| RabbitMQ 消费端 | MQ 线程无上下文 | 手动从 Message Header 读 `tenantId` 并 `execute` |
| 跨模块 RPC 调用 | `executeIgnore` 清空 | 从实体取 `tenantId`，改用 `execute` |

## 关键 API

```java
// 读取当前线程租户
TenantContextHolder.getTenantId()

// 在指定租户上下文中执行（有返回值）
TenantUtils.execute(tenantId, () -> { return result; })

// 在指定租户上下文中执行（无返回值）
TenantUtils.execute(tenantId, () -> { doSomething(); })

// HTTP 请求头名称
"tenant-id"   // 对应 WebFrameworkUtils.HEADER_TENANT_ID
```
