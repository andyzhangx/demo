## Rust 基本语法详解

---

### 1. 变量与可变性

```rust
fn main() {
    // 默认不可变
    let x = 5;
    // x = 6;  // ❌ 编译报错

    // mut 声明可变变量
    let mut y = 10;
    y = 20;  // ✅

    // 遮蔽（Shadowing）— 同名变量可以重新 let，甚至换类型
    let s = "hello";       // &str 类型
    let s = s.len();       // 现在 s 是 usize 类型
    println!("长度: {s}");  // 5

    // 常量 — 必须标注类型，全大写，编译期确定
    const MAX_POINTS: u32 = 100_000;  // 下划线增加可读性
}
```

> **`let` vs `let mut` vs `const`**
> - `let` — 不可变绑定，但可以 shadowing（重新 let）
> - `let mut` — 可变绑定，可以修改值
> - `const` — 编译期常量，永远不可变，不能 shadowing

---

### 2. 数据类型

#### 标量类型（Scalar）

```rust
fn main() {
    // === 整数 ===
    let a: i8 = -128;          // 有符号 8 位：-128 ~ 127
    let b: u8 = 255;           // 无符号 8 位：0 ~ 255
    let c: i32 = 42;           // 默认整数类型
    let d: i64 = 1_000_000;
    let e: usize = 10;         // 指针大小，常用于索引

    // 不同进制
    let hex = 0xff;            // 十六进制
    let oct = 0o77;            // 八进制
    let bin = 0b1010;          // 二进制
    let byte = b'A';           // 字节（u8）

    // === 浮点数 ===
    let f: f64 = 3.14;         // 默认浮点类型（双精度）
    let g: f32 = 2.0;

    // === 布尔 ===
    let t: bool = true;
    let f: bool = false;

    // === 字符 ===（4 字节 Unicode）
    let ch: char = '中';
    let emoji: char = '🦀';
}
```

#### 复合类型（Compound）

```rust
fn main() {
    // === 元组（Tuple）— 固定长度，可以不同类型 ===
    let tup: (i32, f64, &str) = (500, 6.4, "hello");

    // 解构
    let (x, y, z) = tup;
    println!("{x}, {y}, {z}");

    // 索引访问（用 .0 .1 .2）
    println!("第一个: {}", tup.0);

    // 单元类型（空元组）
    let unit: () = ();  // 函数没有返回值时默认返回这个

    // === 数组（Array）— 固定长度，相同类型，栈上分配 ===
    let arr: [i32; 5] = [1, 2, 3, 4, 5];
    println!("第一个: {}", arr[0]);
    println!("长度: {}", arr.len());

    // 初始化相同值
    let zeros = [0; 10];  // [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    // === 切片（Slice）— 数组的引用视图 ===
    let slice: &[i32] = &arr[1..3];  // [2, 3]
    println!("{:?}", slice);
}
```

---

### 3. 字符串

```rust
fn main() {
    // &str — 字符串切片（不可变引用，通常指向编译期字面量）
    let s1: &str = "hello";

    // String — 堆上分配，可增长，可修改
    let mut s2 = String::from("hello");
    s2.push(' ');              // 追加字符
    s2.push_str("world");     // 追加字符串
    println!("{s2}");          // "hello world"

    // 常见转换
    let s3: String = "hello".to_string();  // &str → String
    let s4: &str = &s3;                    // String → &str（自动解引用）

    // 格式化
    let name = "Rust";
    let greeting = format!("Hello, {name}!");

    // 长度（注意：UTF-8 字节数，不是字符数）
    let chinese = "你好";
    println!("字节数: {}", chinese.len());        // 6
    println!("字符数: {}", chinese.chars().count()); // 2

    // 遍历字符
    for c in "hello".chars() {
        print!("{c} ");  // h e l l o
    }
}
```

> **`&str` vs `String` 经验法则：**
> - 函数参数 → 优先用 `&str`（更通用）
> - 需要拥有/修改数据 → 用 `String`

---

### 4. 函数

```rust
// 基本语法：fn 名称(参数: 类型) -> 返回类型
fn add(a: i32, b: i32) -> i32 {
    a + b  // 最后一个表达式就是返回值（注意没有分号！）
}

// 没有返回值（返回 ()）
fn say_hello(name: &str) {
    println!("Hello, {name}!");
}

// 也可以用 return 提前返回
fn abs(x: i32) -> i32 {
    if x < 0 {
        return -x;  // 提前返回用 return + 分号
    }
    x  // 最后一行不用 return
}

// 多返回值 — 用元组
fn swap(a: i32, b: i32) -> (i32, i32) {
    (b, a)
}

fn main() {
    let sum = add(3, 5);
    say_hello("World");
    let (x, y) = swap(1, 2);
    println!("{x}, {y}");  // 2, 1
}
```

> ⚠️ **有分号 vs 没分号**
> ```rust
> a + b   // 表达式（有值，作为返回值）
> a + b;  // 语句（没有值，返回 ()）
> ```

---

### 5. 控制流

#### if/else

```rust
fn main() {
    let n = 7;

    // 条件不需要括号
    if n > 10 {
        println!("大于 10");
    } else if n > 5 {
        println!("5 到 10 之间");
    } else {
        println!("5 以下");
    }

    // if 是表达式，可以赋值
    let label = if n > 0 { "正数" } else { "非正数" };
    println!("{label}");
}
```

#### 循环

```rust
fn main() {
    // === loop — 无限循环 ===
    let mut count = 0;
    let result = loop {
        count += 1;
        if count == 5 {
            break count * 10;  // break 可以带返回值
        }
    };
    println!("result = {result}");  // 50

    // 嵌套循环用标签
    'outer: loop {
        loop {
            break 'outer;  // 跳出外层
        }
    }

    // === while ===
    let mut n = 3;
    while n > 0 {
        println!("{n}");
        n -= 1;
    }

    // === for — 最常用 ===
    // 范围
    for i in 0..5 {
        print!("{i} ");    // 0 1 2 3 4
    }

    for i in 0..=5 {
        print!("{i} ");    // 0 1 2 3 4 5（包含 5）
    }

    // 遍历数组
    let colors = ["red", "green", "blue"];
    for color in colors {
        println!("{color}");
    }

    // 带索引遍历
    for (i, color) in colors.iter().enumerate() {
        println!("{i}: {color}");
    }

    // 反向
    for i in (1..=5).rev() {
        print!("{i} ");    // 5 4 3 2 1
    }
}
```

---

### 6. 模式匹配

```rust
fn main() {
    let x = 3;

    // === match — 必须穷举所有可能 ===
    match x {
        1 => println!("一"),
        2 => println!("二"),
        3 | 4 => println!("三或四"),     // 多个值
        5..=10 => println!("5到10"),     // 范围
        _ => println!("其他"),           // _ 是通配符
    }

    // match 也是表达式
    let text = match x {
        1 => "one",
        2 => "two",
        _ => "other",
    };

    // === if let — match 的简写（只关心一种情况）===
    let some_val: Option<i32> = Some(42);

    if let Some(v) = some_val {
        println!("值是 {v}");
    }

    // 等价于：
    // match some_val {
    //     Some(v) => println!("值是 {v}"),
    //     _ => {}
    // }

    // === while let ===
    let mut stack = vec![1, 2, 3];
    while let Some(top) = stack.pop() {
        println!("弹出: {top}");  // 3, 2, 1
    }

    // === 解构 ===
    let point = (3, 5);
    let (x, y) = point;

    struct Color { r: u8, g: u8, b: u8 }
    let c = Color { r: 255, g: 0, b: 128 };
    let Color { r, g, b } = c;
    println!("r={r}, g={g}, b={b}");
}
```

---

### 7. 运算符

```rust
fn main() {
    // 算术
    let a = 10 + 3;    // 13
    let b = 10 - 3;    // 7
    let c = 10 * 3;    // 30
    let d = 10 / 3;    // 3（整数除法）
    let e = 10 % 3;    // 1（取余）
    let f = 10.0 / 3.0; // 3.333...（浮点除法）

    // 比较（返回 bool）
    // ==  !=  >  <  >=  <=

    // 逻辑
    // &&（与）  ||（或）  !（非）

    // 位运算
    // &（与） |（或） ^（异或） !（取反） <<（左移） >>（右移）

    // ⚠️ Rust 没有 ++ 和 --
    let mut x = 5;
    x += 1;  // 用 += 代替 ++
    x -= 1;  // 用 -= 代替 --

    // ⚠️ Rust 不自动类型转换
    let a: i32 = 5;
    let b: f64 = a as f64;  // 必须显式转换
    let c: u8 = 255;
    let d: i8 = c as i8;    // 溢出！结果是 -1
}
```

---

### 8. 注释

```rust
// 单行注释

/* 
   多行注释
   （不常用）
*/

/// 文档注释（用于函数/结构体上方，支持 Markdown）
/// 会被 `cargo doc` 生成 HTML 文档
///
/// # Examples
/// ```
/// let result = add(2, 3);
/// assert_eq!(result, 5);
/// ```
fn add(a: i32, b: i32) -> i32 {
    a + b
}

//! 模块级文档注释（放在文件开头）
//! 描述整个模块的用途
```

---

### 9. 输入输出

```rust
use std::io;

fn main() {
    // === 输出 ===
    println!("换行输出");
    print!("不换行");
    eprintln!("输出到 stderr");

    // 格式化
    let name = "Rust";
    let ver = 2024;
    println!("{name} {ver}");              // 变量直接嵌入
    println!("{0} is {1}, {0}!", name, "cool"); // 位置参数
    println!("{:>10}", "right");           // 右对齐，宽度 10
    println!("{:<10}", "left");            // 左对齐
    println!("{:0>5}", 42);               // 00042
    println!("{:.2}", 3.14159);           // 3.14（保留两位小数）
    println!("{:?}", vec![1, 2, 3]);      // Debug 格式: [1, 2, 3]
    println!("{:#?}", vec![1, 2, 3]);     // 美化 Debug 格式

    // === 输入 ===
    println!("请输入你的名字:");
    let mut input = String::new();
    io::stdin()
        .read_line(&mut input)
        .expect("读取失败");

    let input = input.trim();  // 去掉末尾换行
    println!("你好, {input}!");

    // 解析为数字
    let num: i32 = input.trim().parse().unwrap_or(0);
}
```

---

### 10. 类型转换与类型别名

```rust
fn main() {
    // as — 基本类型转换
    let x: i32 = 42;
    let y: f64 = x as f64;
    let z: u8 = x as u8;

    // From / Into — 更安全的转换
    let s: String = String::from("hello");
    let n: i64 = i64::from(42i32);

    // 等价写法
    let n: i64 = 42i32.into();

    // parse — 字符串转数字
    let num: i32 = "42".parse().unwrap();
    let num = "42".parse::<f64>().unwrap();

    // toString
    let s = 42.to_string();
}

// 类型别名
type Meters = f64;
type Result<T> = std::result::Result<T, String>;
```

---

### 📋 语法速查表

| 语法 | Rust | 对比 Go/Python |
|---|---|---|
| 变量 | `let x = 5;` | `x := 5` / `x = 5` |
| 可变变量 | `let mut x = 5;` | 默认可变 |
| 常量 | `const X: i32 = 5;` | `const X = 5` |
| 函数 | `fn foo(x: i32) -> i32` | `func foo(x int) int` |
| 字符串 | `String` + `&str` | `string` |
| 数组 | `[i32; 5]`（固定）/ `Vec<i32>`（动态） | `[5]int` / `[]int` |
| 空值 | `Option<T>` (`Some`/`None`) | `nil` / `None` |
| 错误 | `Result<T, E>` (`Ok`/`Err`) | `error` / `Exception` |
| 输出 | `println!("{}",x)` | `fmt.Println(x)` |
| 循环 | `for i in 0..10` | `for i := 0; i < 10; i++` |
| 条件 | `if x > 0 { }` | 相同 |
| 没有 | `null`/`nil`、`try-catch`、`++/--`、隐式类型转换 | — |

---

### 🎯 Rust 语法核心要点总结

1. **变量默认不可变**，需要 `mut` 才能改
2. **没有 null**，用 `Option<Some/None>` 代替
3. **没有异常**，用 `Result<Ok/Err>` 代替
4. **表达式 vs 语句**：没分号是表达式（有值），有分号是语句
5. **类型不会隐式转换**，必须用 `as` 或 `From/Into`
6. **`match` 必须穷举**所有可能
7. **宏用 `!`**：`println!`、`vec!`、`format!` 都是宏不是函数
