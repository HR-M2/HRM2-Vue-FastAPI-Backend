# HRM2 API 文档

## 概述

HRM2 企业招聘管理系统的 API 文档集合。

## 在线文档

- **Swagger UI**: http://127.0.0.1:8000/docs - 交互式 API 文档
- **ReDoc**: http://127.0.0.1:8000/redoc - 美观的只读文档
- **OpenAPI JSON**: http://127.0.0.1:8000/openapi.json - OpenAPI 3.0 规范

## 模块文档

### API 接口文档

- [沉浸式面试 API](./api/immersive.md) - 双摄像头面试、心理分析、实时数据处理

### 即将添加

- 岗位管理 API
- 简历管理 API  
- 应聘申请 API
- 简历筛选 API
- 视频分析 API
- 面试辅助 API
- 综合分析 API

## 快速开始

1. **启动服务**
   ```bash
   python run.py --reload
   ```

2. **访问文档**
   - 打开浏览器访问 http://127.0.0.1:8000/docs
   - 查看所有可用的 API 接口

3. **测试接口**
   - 在 Swagger UI 中直接测试 API
   - 查看请求/响应示例

## 开发指南

### 添加新的 API 文档

1. 在 `docs/api/` 目录下创建新的 Markdown 文件
2. 按照现有格式编写文档
3. 在本文件中添加链接

### 文档规范

- 使用 Markdown 格式
- 包含完整的请求/响应示例
- 提供使用流程说明
- 注明错误处理方式

---

**版本**: v2.0.0  
**更新时间**: 2024-01-17