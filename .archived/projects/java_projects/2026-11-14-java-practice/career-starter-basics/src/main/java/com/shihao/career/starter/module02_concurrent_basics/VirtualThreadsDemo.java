package com.shihao.career.starter.module02_concurrent_basics;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.*;

/**
 * <h2>知识点五：Java 21 标志性王炸特性 —— 虚拟线程（Virtual Threads, JEP 444）</h2>
 *
 * <h3>【为什么初学者必须掌握？】</h3>
 * 1. <b>传统平台线程（Platform Thread）</b>：映射到操作系统内核线程，每个线程默认占用 1MB 栈内存，
 * 操作系统频繁上下文切换开销极大。单机如果创建几千个线程就会报 {@code OutOfMemoryError: unable to create native thread}，
 * 这也是为什么老一代 Java 必须小心翼翼地配置线程池核心数与最大数。<br>
 * 2. <b>Java 21 虚拟线程</b>：JVM 在用户态自行调度的轻量级线程，初始仅占用几百字节！
 * 遇到网络 I/O 阻塞（如 HTTP 调用、数据库查询、Redis 读写）时，虚拟线程会自动从内核载体线程（Carrier Thread）上“卸载”（Unmount），
 * 载体线程可以立刻去执行其他任务；当 I/O 返回后再自动挂载（Mount）恢复执行。
 *
 * <h3>【对标简历实战场景】</h3>
 * 对应《收银中台》中多渠道异步支付通知回调、高并发探活，以及《智能客服》中千级并发 WebSocket/长连接连接池管理。
 * 单机轻松支撑 10 万+ 并发 I/O 密集型任务，彻底摆脱线程池打满拒绝与死锁的阴影！
 */
public class VirtualThreadsDemo {

    /**
     * 1. 使用 Thread.ofVirtual() 创建并启动单条虚拟线程
     */
    public String runSingleVirtualThread(String taskName) throws InterruptedException {
        StringBuilder result = new StringBuilder();

        Thread vThread = Thread.ofVirtual().name("vthread-" + taskName).start(() -> {
            boolean isVirtual = Thread.currentThread().isVirtual();
            result.append(String.format("任务 [%s] 在虚拟线程中运行，isVirtual = %b", taskName, isVirtual));
        });

        // 等待虚拟线程执行完毕
        vThread.join();
        return result.toString();
    }

    /**
     * 2. 使用 Java 21 新增的虚拟线程池（newVirtualThreadPerTaskExecutor）批量执行海量任务
     * 核心设计哲学：【任务即线程】——不需要复用虚拟线程，每个 I/O 任务随用随建，完结即销毁！
     *
     * @param taskCount 任务数量（如 1000 个模拟并发 I/O 任务）
     * @return 成功完成的任务总数
     */
    public int executeConcurrentTasksWithVirtualThreads(int taskCount) {
        List<Future<Boolean>> futures = new ArrayList<>(taskCount);

        // try-with-resources 会自动关闭 ExecutorService，并隐式等待所有任务完成（结构化并发思想）
        try (ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < taskCount; i++) {
                final int taskId = i;
                futures.add(executor.submit(() -> {
                    // 模拟网络 I/O 阻塞耗时 10 毫秒（例如向银行拉美 PSP 接口发起探活）
                    Thread.sleep(10);
                    return true;
                }));
            }
        } // 退出 try 块时自动 awaitTermination

        int successCount = 0;
        for (Future<Boolean> f : futures) {
            try {
                if (f.get()) {
                    successCount++;
                }
            } catch (Exception ignored) {}
        }
        return successCount;
    }
}
