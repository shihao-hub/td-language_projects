package com.shihao.career.starter.module04_spring_basics;

import com.shihao.career.starter.module04_spring_basics.action.OrderAction;
import org.springframework.context.ApplicationContext;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;

/**
 * <h2>知识点六：Spring 核心容器与轻量级配置化状态机（零重型引擎）</h2>
 *
 * <h3>【为什么初学者必须掌握？】</h3>
 * 大多数刚写 Java 的同学只知道在字段上写 {@code @Autowired} 注入固定对象。
 * 殊不知 Spring 最强大的特性就是 {@link ApplicationContext}（IoC 容器本身）：
 * 它是一个可以在运行时通过名称/编码动态查找并实例化 Bean 的超级对象工厂！
 *
 * <h3>【对标简历最硬核设计】</h3>
 * 对应《收银中台》第 3 点：
 * <ul>
 *   <li>业务痛点：多国退款业务分支极多，写 if-else 嵌套会膨胀到几千行不可维护；</li>
 *   <li>解法：设计配置表（四元组：场景+当前状态+事件），查表得到 {@code trigger_action} 编码；</li>
 *   <li>执行：引擎通过 {@code applicationContext.getBean(trigger_action)} 动态拿到实现类执行！</li>
 *   <li>收益：新增业务动作只需要写一个新类加 {@code @Component("NEW_ACTION")} 并在数据库插一行配置，<b>核心引擎代码 0 修改、系统免发版上线！</b></li>
 * </ul>
 */
@Service
public class DynamicStateMachineEngine {

    private final ApplicationContext applicationContext;

    /**
     * 模拟数据库配置表中的流转规则：
     * (当前状态, 触发事件) -> 规则(目标状态, 关联执行的 Spring Bean 名字)
     */
    public record TransitionRule(String currentStatus, String triggerEvent, String nextStatus, String actionBeanName) {}

    private final Map<String, TransitionRule> ruleTable = new HashMap<>();

    public DynamicStateMachineEngine(ApplicationContext applicationContext) {
        this.applicationContext = applicationContext;
        initMockConfigTable();
    }

    /**
     * 初始化模拟配置表数据（在真实大厂项目中，这些配置保存在数据库 refund_state_flow_config 表中）
     */
    private void initMockConfigTable() {
        // 规则 1：待接单 + 用户支付成功事件 -> 变更为备餐中 + 触发通知商家动作
        registerRule(new TransitionRule("WAIT_ACCEPT", "PAY_SUCCESS", "PREPARING", "NOTIFY_MERCHANT"));

        // 规则 2：备餐中 + 商家出餐完成事件 -> 变更为配送中 + 触发派单动作
        registerRule(new TransitionRule("PREPARING", "MEAL_READY", "DELIVERING", "DISPATCH_RIDER"));

        // 规则 3：待接单 + 商家接单超时事件 -> 变更为已取消 + 触发自动原路退款动作
        registerRule(new TransitionRule("WAIT_ACCEPT", "TIMEOUT_REJECT", "CANCELLED", "AUTO_REFUND"));
    }

    private void registerRule(TransitionRule rule) {
        String key = buildKey(rule.currentStatus(), rule.triggerEvent());
        ruleTable.put(key, rule);
    }

    private String buildKey(String status, String event) {
        return status.toUpperCase() + "##" + event.toUpperCase();
    }

    /**
     * 执行状态机流转核心引擎
     *
     * @param orderId       订单号
     * @param currentStatus 当前主单状态
     * @param event         触发事件
     * @return 流转结果描述
     */
    public TransitionResult fireEvent(String orderId, String currentStatus, String event) {
        String key = buildKey(currentStatus, event);
        TransitionRule rule = ruleTable.get(key);

        if (rule == null) {
            throw new IllegalStateException(String.format("【非法状态流转】当前状态 [%s] 无法响应事件 [%s]，阻断流转！", currentStatus, event));
        }

        // 核心技术点：通过 Spring 容器动态加载动作 Bean
        String actionBeanName = rule.actionBeanName();
        OrderAction action = applicationContext.getBean(actionBeanName, OrderAction.class);
        
        // 执行动作
        String actionLog = action.execute(orderId);

        return new TransitionResult(
                orderId,
                currentStatus,
                rule.nextStatus(),
                event,
                actionBeanName,
                actionLog
        );
    }

    public record TransitionResult(
            String orderId,
            String fromStatus,
            String toStatus,
            String event,
            String executedActionBean,
            String executionDetail
    ) {}
}
