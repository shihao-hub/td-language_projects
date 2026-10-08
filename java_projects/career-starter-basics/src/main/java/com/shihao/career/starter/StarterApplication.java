package com.shihao.career.starter;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * <h1>第一阶段：Java 核心基石与 Spring 状态机引导工程</h1>
 * <p>
 * 本项目面向大学刚毕业、拥有数月 Java 基础的学习者，
 * 旨在将您简历中三大项目（收银中台、智能客服与质检、智能排障 Agent）
 * 所依赖的最基础、最核心的 Java 语言特性与 Spring 框架机制提炼为极简、直观的代码实现。
 * </p>
 */
@SpringBootApplication
public class StarterApplication {

    public static void main(String[] args) {
        SpringApplication.run(StarterApplication.class, args);
        System.out.println("==================================================================");
        System.out.println(">>> 01-career-starter-basics 启动成功！");
        System.out.println(">>> 访问 http://localhost:8080/api/demo/health 即可体验基础端点");
        System.out.println("==================================================================");
    }
}
