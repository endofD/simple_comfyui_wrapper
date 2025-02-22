# comfyui 工作流 封装 api

简单的 ComfyUI 后端 WebSocket API 封装  
简单的前端 + RESTful API 后端  

功能：
- REST API 
- 用户管理
- 简单的 FIFO 调度器
- 保留 ComfyUI 输出的图片
- 后台和comfyui 分离设计，comfyui可以是在内网 
- 逻辑简单 容易扩展

---

## REST API

轻量级的 Flask 框架。

觉得gpu资源太慢,所以什么分布式什么负载均衡有点 超脱了:)

---

## 用户管理

用户凭证存储在一个 JSON 文件中：

```json
{
  "users": {
    "user1": "password1",
    "user2": "password2"
  }
}
```

---

## FIFO 调度器

- 每个用户只允许 **一个** 运行实例。
- 如果其他用户正在执行，请求将被放入队列并返回队列编号。
- **没有队列监控代码**；你需要在前端实现自己的监控逻辑。
- **结果会被缓存**。后续提交将被 **忽略**，并从 **缓存** 中获取结果。

---

## 保留所有上传和 ComfyUI 生成的图片

- `data`：此目录存储 ComfyUI API 的工作流文件。
- `uploads`：此目录存储用户上传的图片。
- `comfyui_img`：此目录存储 ComfyUI 生成的图片。

---

## 前端示例

提供了两个示例，分别用于文本输入和图片输入。

---

## 安装

1. 创建虚拟环境：
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 更新配置：
   - 设置 `COMFYUI_SERVER_ADDRESS = "127.0.0.1:8188"`
   - 设置 `FLASK_ADDR = 'http://127.0.0.1:5000'`

---

## 示例截图

![示例图片 1](https://github.com/endofD/simple_comfyui_wrapper/raw/refs/heads/main/screen_shot/1.png)

![示例图片 2](https://github.com/endofD/simple_comfyui_wrapper/raw/refs/heads/main/screen_shot/2.png)

![示例图片 3](https://github.com/endofD/simple_comfyui_wrapper/raw/refs/heads/main/screen_shot/3.png)

![示例图片 4](https://github.com/endofD/simple_comfyui_wrapper/raw/refs/heads/main/screen_shot/4.png)

---

## 添加新工作流

1. 将工作流 API 文件复制到 `data` 目录中。

2. 在 Flask 应用中创建一个新路由：
   ```python
   @app.route('/api/new_api', methods=['POST'])
   ```

3. 加载/覆盖值并 **填充** **task**：
   ```python
   (prompt, ret,) = get_promp_from_json('api_test.json')
   data = request.get_json()
   text = data.get('text')
   task['prompt'] = prompt
   task['text'] = text
   task['call'] = api1
   ```

4. 定义 API 函数：
   ```python
   def api1(task):  # t2i，输入：文本
       prompt = task['prompt']
       prompt['42']['inputs']['text'] = task['text']
       output_images = process_comfyui(prompt)
       (p,) = save_img_result("comfyui_img", "t2i", output_images[0])
       return f"{FLASK_ADDR}/{p}"
   ```

5. 按照此模板添加新工作流。

---

祝你玩得开心！ 🚀
