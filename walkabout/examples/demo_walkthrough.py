"""
Walkabout 功能演示 — 涵盖核心特性与边界情况

运行方式：
  1. 在 Walkabout 编辑器中打开此文件
  2. 点击 ▶ 执行
  3. 在回放面板中逐帧浏览

也可以通过 CLI 直接执行（需在项目目录下）：
  python -c "
  from walkabout.core.execute import execute
  trace = execute('demo_walkthrough', inspect_all_variables=False)
  print(f'Trace generated: {len(trace.steps)} steps')
  "
"""
from execute_util import text, image, link, system_text


# ── 1. 基本 Markdown 渲染 ──────────────────────────────────────

def basic_text():
    text("# Walkabout 功能演示\n\n这是一个 **交互式代码讲解** 工具。")
    text("支持 *斜体*、`行内代码`、~~删除线~~ 等 Markdown 语法。")
    text("- 列表项 1\n- 列表项 2\n- 列表项 3", verbatim=False)


# ── 2. 变量追踪 (@inspect) ─────────────────────────────────────

def variable_tracking():
    # 基础类型
    count = 42              # @inspect count
    name = "Walkabout"      # @inspect name
    pi = 3.14159            # @inspect pi
    is_active = True        # @inspect is_active

    # 集合类型
    fruits = ["apple", "banana", "cherry"]  # @inspect fruits
    config = {"theme": "dark", "port": 8000}  # @inspect config
    unique_ids = {1, 2, 3, 4, 5}  # @inspect unique_ids
    coords = (10.0, 20.0)  # @inspect coords

    # 空值和边界
    empty_list = []  # @inspect empty_list
    none_val = None  # @inspect none_val
    empty_str = ""   # @inspect empty_str
    zero = 0         # @inspect zero


# ── 3. 字符串操作 ──────────────────────────────────────────────

def string_operations():
    greeting = "Hello, Walkabout!"  # @inspect greeting
    parts = greeting.split(",")     # @inspect parts
    upper = greeting.upper()        # @inspect upper
    length = len(greeting)          # @inspect length
    sub = greeting[7:16]            # @inspect sub


# ── 4. 列表与字典操作 ──────────────────────────────────────────

def list_dict_ops():
    items = [3, 1, 4, 1, 5, 9, 2, 6]  # @inspect items
    items.append(5)  # @inspect items
    items.sort()     # @inspect items
    popped = items.pop()  # @inspect popped
    sliced = items[2:5]  # @inspect sliced

    data = {"a": 1}  # @inspect data
    data["b"] = 2    # @inspect data
    data["c"] = 3    # @inspect data
    keys = list(data.keys())  # @inspect keys


# ── 5. 函数调用与 @stepover ────────────────────────────────────

def helper_multiply(x, y):
    """被 stepover 跳过内部细节的辅助函数。"""
    result = x * y
    return result

def helper_expensive(n):
    """另一个辅助函数——stepover 会跳过其逐行执行。"""
    total = 0
    for i in range(n):
        total += i
    return total

def function_calls():
    a = 6  # @inspect a
    b = 7  # @inspect b
    # @stepover — 跳过 helper_multiply 内部细节，直接显示结果
    product = helper_multiply(a, b)  # @inspect product  @stepover
    text(f"计算结果: {a} × {b} = {product}")

    # 复杂的循环——用 stepover 跳过
    total = helper_expensive(100)  # @inspect total  @stepover
    text(f"累加结果: {total}")


# ── 6. 嵌套函数调用 ────────────────────────────────────────────

def inner(x):
    return x ** 2

def middle(x):
    return inner(x) + 1

def nested_calls():
    val = 5  # @inspect val
    result = middle(val)  # @inspect result  @stepover
    text(f"嵌套调用: middle({val}) = {result}")


# ── 7. Shell 命令 ──────────────────────────────────────────────

def shell_demo():
    text("### 系统命令输出")
    system_text(["python", "--version"])
    system_text(["python", "-c", "import sys; print(f'Python {sys.version_info.major}.{sys.version_info.minor}')"])


# ── 8. 图片与链接 ──────────────────────────────────────────────

def media_demo():
    text("### 资源引用")

    # 链接到外部资源
    link("https://github.com/CraneBW/walkabout", title="Walkabout on GitHub")

    # 链接到函数（指向当前文件内代码）
    link(variable_tracking, title="跳转到变量追踪函数")


# ── 9. 多变量同⾏追踪 ──────────────────────────────────────────

def multi_inspect():
    x, y, z = 10, 20, 30  # @inspect x, @inspect y, @inspect z
    total = x + y + z  # @inspect total
    avg = total / 3  # @inspect avg
    text(f"统计: 总和={total}, 平均={avg:.1f}")


# ── 10. 边界情况 ──────────────────────────────────────────────

def edge_cases():
    # 非常大的整数
    big = 2 ** 100  # @inspect big

    # 浮点数精度
    float_sum = 0.1 + 0.2  # @inspect float_sum

    # 嵌套数据结构
    nested = {"level1": {"level2": {"level3": "deep"}}}  # @inspect nested

    # 列表推导式
    squares = [x * x for x in range(5)]  # @inspect squares

    # 布尔运算
    t = True and False  # @inspect t
    f = True or False   # @inspect f
    n = not True        # @inspect n


# ── 11. 类型互转 ──────────────────────────────────────────────

def type_coercion():
    num_str = "256"  # @inspect num_str
    num_int = int(num_str)  # @inspect num_int
    num_float = float(num_int)  # @inspect num_float
    back_to_str = str(num_float)  # @inspect back_to_str


# ── 12. 数学公式渲染（MathJax） ────────────────────────────────

def math_formulas():
    text(r"### 数学公式")

    # 行内公式
    text(r"欧拉恒等式: $e^{i\pi} + 1 = 0$")
    text(r"勾股定理: $a^2 + b^2 = c^2$")

    # 块级公式
    text(r"$$ \frac{-b \pm \sqrt{b^2 - 4ac}}{2a} $$")

    text(r"$$ \int_{0}^{\infty} e^{-x^2} \, dx = \frac{\sqrt{\pi}}{2} $$")

    text(r"$$ \nabla \times \mathbf{E} = -\frac{\partial \mathbf{B}}{\partial t} $$")

    text(r"$$ \sum_{k=1}^{n} k^2 = \frac{n(n+1)(2n+1)}{6} $$")


# ── 13. 条件逻辑 ──────────────────────────────────────────────

def conditionals():
    score = 85  # @inspect score

    if score >= 90:
        grade = "A"  # @inspect grade
    elif score >= 80:
        grade = "B"  # @inspect grade
    elif score >= 70:
        grade = "C"
    else:
        grade = "D"

    text(f"得分 {score} → 等级 {grade}")


# ── 13. 循环 ──────────────────────────────────────────────────

def loop_demo():
    items = ["a", "b", "c", "d"]  # @inspect items
    result = ""  # @inspect result

    for item in items:
        result = result + item  # @inspect result
        text(f"追加 '{item}' → \"{result}\"")


# ── main ────────────────────────────────────────────────────────

def main():
    text("# Walkabout 功能演示\n\n逐帧回放验证所有核心特性。")

    basic_text()
    text("---\n## 变量追踪")

    variable_tracking()
    text("---\n## 字符串操作")

    string_operations()
    text("---\n## 集合操作")

    list_dict_ops()
    text("---\n## 函数与 Stepover")

    function_calls()
    text("---\n## 嵌套调用")

    nested_calls()
    text("---\n## Shell 命令")

    shell_demo()
    text("---\n## 链接与引用")

    media_demo()
    text("---\n## 多变量追踪")

    multi_inspect()
    text("---\n## 边界情况")

    edge_cases()
    text("---\n## 类型转换")

    type_coercion()
    text("---\n## 数学公式")

    math_formulas()
    text("---\n## 条件分支")

    conditionals()
    text("---\n## 循环")

    loop_demo()

    text("\n---\n✅ 演示完成！请使用回放面板逐帧浏览执行过程。")
