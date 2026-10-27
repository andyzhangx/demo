# 理解 LLM 的 Transformer 层与 KV cache

> 核心结论：**同一批 token 会经过模型的不同层，但每层计算出来的表示和 K/V 通常都不同。KV cache 不是把同一段文字存很多遍，而是保存各层各自的 attention 中间结果，供后续生成复用。**
>
> 本文以常见的、使用 causal self-attention 的 decoder-only Transformer 为例。文中的“32 层”和 token 划分只是教学假设，不代表某个具体模型。混合架构、滑动窗口 attention、跨层 KV 共享等特殊设计需要另外讨论。

## 1. “At each layer” 是什么意思？

在介绍 prefill 时，我们可能会说：

> As the model runs, it saves the attention keys and values for the processed positions at each layer. That’s the KV cache.

这里的 **at each layer** 指的是：

> **在 Transformer 的每一层里，分别保存该层为已处理的 token 计算出来的 Key 和 Value。**

不是整个模型只共用一份 K/V，也不是把同一份 K/V 原样复制到每一层。

## 2. 模型里的“层”是什么？

一个 Transformer 模型由多个 Transformer block 依次组成。这里说的“层”，通常就是指这些 block，而不是一个 attention head。

每个 block 通常包含 attention、前馈网络（MLP），以及归一化、残差连接等结构。具体排列顺序取决于模型。

可以先把模型理解成一条多阶段处理流水线：

```text
输入 token
    ↓
Embedding：变成向量表示
    ↓
第 1 层 Transformer block
    ↓
第 2 层 Transformer block
    ↓
   ...
    ↓
第 32 层 Transformer block
    ↓
最终归一化 / 输出投影等
    ↓
下一个 token 的 logits（各候选 token 的分数）
```

每一层都在上一层的处理结果上继续计算。多层结构让模型能够逐步组合、变换和利用上下文信息，而不只是做一次 attention。

不过，不应该机械地理解成“第一层负责语法、第二层负责语义、第三层负责推理”。这些能力通常分布在多个层和计算路径中，没有这么整齐的职责划分。

## 3. 同样是 32 层，内容不是一样的吗？

**token 的位置和标签一样，不代表对应的向量内容一样。**

以 prompt 中的 `Kubernetes` 为例：

```text
“Kubernetes” 对应的初始向量 h₀
                ↓ 第 1 层处理
           新的表示 h₁
                ↓ 第 2 层处理
           新的表示 h₂
                ↓
               ...
                ↓ 第 32 层处理
           新的表示 h₃₂
```

`h₀、h₁、h₂……` 通常是不同的向量。每层不是重新读取同一个原始单词，而是处理上一层输出的表示。

因此，如果一张图的每一层都写着 `Kubernetes`，这个单词只是用于标记“这是哪个 token 位置”，并不表示每一层存储的数据相同。

## 4. 每层为什么会有不同的 Q、K、V？

在每层的 attention 中，模型会根据这一层的输入表示，计算 Query、Key 和 Value：

- **Query（Q）**：当前位置用来“查找信息”的向量。
- **Key（K）**：用于和 Query 匹配、决定关注哪些位置的向量。
- **Value（V）**：根据 attention 权重进行信息汇总的向量。

这是帮助理解的类比；实际计算是向量和矩阵运算，不是数据库中的精确键值查找。

省略归一化、head 拆分和位置编码等细节后，可以简化为：

```text
第 ℓ 层的输入表示 × 第 ℓ 层的 Query 投影参数 → Qℓ
第 ℓ 层的输入表示 × 第 ℓ 层的 Key 投影参数   → Kℓ
第 ℓ 层的输入表示 × 第 ℓ 层的 Value 投影参数 → Vℓ
```

不同层的输入表示不同，投影参数通常也不同，所以同一个 token 的 `K₁/V₁` 和 `K₂/V₂` 通常不同。

**第一层的 K/V 不能直接替代第二层的 K/V，最后一层的 K/V 也不能作为所有层的通用缓存。**

另外，layer 和 head 是两个不同维度：一个 attention 层内部还可以包含多个 head。使用 GQA 或 MQA 的模型，KV head 数量可以少于 Query head 数量。

## 5. 用一个五个 token 的 prompt 看 prefill

假设输入是：

```text
What does Kubernetes do?
```

为了方便画图，假设它被分成五个 token：

```text
位置 1     位置 2     位置 3         位置 4     位置 5
What       does       Kubernetes     do         ?
```

**这只是教学示例，不是真实 tokenizer 的输出。** 实际模型可能拆出不同的 token，还可能包含空格编码、特殊 token 和 chat template。

### 5.1 一起计算，不代表能看到未来

Prefill 可以在每一层中并行处理多个已知的 prompt 位置，但仍然遵守 causal attention：每个位置只能关注自己和前面的位置。

```text
What        → What
 does       → What, does
 Kubernetes → What, does, Kubernetes
 do         → What, does, Kubernetes, do
 ?          → What, does, Kubernetes, do, ?
```

因此，`Kubernetes` 这个位置可以结合前面的 `What does`，但不能看到后面的 `do ?`。最后的 `?` 位置可以结合整个 prompt。

“并行处理 prompt 位置”也不代表 32 个依赖前层结果的 Transformer block 可以同时完成；各层的计算仍然有先后依赖。

### 5.2 每层缓存什么？

假设有 32 个 attention 层，prefill 完成后，逻辑上会保存：

```text
第 1 层：
  K₁(What), K₁(does), K₁(Kubernetes), K₁(do), K₁(?)
  V₁(What), V₁(does), V₁(Kubernetes), V₁(do), V₁(?)

第 2 层：
  K₂(What), K₂(does), K₂(Kubernetes), K₂(do), K₂(?)
  V₂(What), V₂(does), V₂(Kubernetes), V₂(do), V₂(?)

...

第 32 层：
  K₃₂(What), K₃₂(does), K₃₂(Kubernetes), K₃₂(do), K₃₂(?)
  V₃₂(What), V₃₂(does), V₃₂(Kubernetes), V₃₂(do), V₃₂(?)
```

括号里的单词只是位置标签。每个 K/V 实际包含向量数据，还有 KV head、head dimension 等维度。

KV cache 保存的是这些 **attention 中间结果**，不是原始文本，不是模型权重，也不是各层的全部计算结果。

### 5.3 第一个输出 token 是什么时候选出的？

在通常的自回归生成流程中，prefill 最后一个 prompt 位置的最终表示，经过输出投影得到下一个 token 的 logits。系统再按 greedy、sampling 等策略选出第一个输出 token。

例如，教学上假设第一个输出 token 是 `Kubernetes`。这并不意味着模型一定会给出这个答案，也不意味着真实 tokenizer 一定把这个词编码为单个 token。

这里要区分：

- **选出了 `Kubernetes`**：已经获得第一个输出 token。
- **把这个新 token 再送入模型**：为它计算各层的 K/V，并预测它后面的 token。

前者通常利用 prefill 的输出完成；后者是接下来的一步 decode。

## 6. Decode 如何复用每层的 KV cache？

在标准逐 token decode 中，新 token 仍然需要经过模型的所有层。

以刚选出的输出 token `Kubernetes` 为例：

1. 到第 1 层，计算新 token 在这一层的 Q/K/V，使用第 1 层缓存的历史 K/V 和新 token 的 K/V 做 attention，并把新的 K/V 加入这一层的缓存。
2. 到第 2 层，处理第 1 层的输出，计算第 2 层的 Q/K/V，并使用、更新第 2 层的缓存。
3. 按同样的方式经过后续各层。
4. 在最后得到下一个输出 token 的分数，再选出下一个 token。

```text
新 token → 第 1 层  ← 第 1 层的历史 K/V
              ↓
           第 2 层  ← 第 2 层的历史 K/V
              ↓
             ...
              ↓
           第 32 层 ← 第 32 层的历史 K/V
              ↓
        预测下一个 token
```

**每一层使用自己的 KV cache，而不是使用同一份共享内容。**

这种逐 token 描述不覆盖 speculative decoding 等一次验证多个候选 token 的特殊流程，但按层保存和使用 K/V 的核心概念仍然适用。

## 7. 为什么历史 K/V 可以复用？

在标准 causal attention 中，过去的位置看不到后来追加的 token。固定模型和已有前缀后，追加一个新 token 不需要重新改变已有位置的各层表示和 K/V。

因此，这些历史结果可以被缓存下来，在后续步骤复用。

KV cache 主要避免的是：**为了生成下一个 token，重新计算整个历史前缀的各层 K/V 及相关前向计算。**

它并不意味着：

- 新 token 可以跳过所有 Transformer 层。
- Attention 不再需要访问历史数据。
- 输出越长，每一步 decode 的开销仍然完全不变。

对于常见的全上下文 attention，新 token 的 Query 仍要与历史 Key 进行匹配，并汇总历史 Value。上下文变长后，缓存容量和读取这些数据的开销也会增加。

通常不需要为此缓存历史 Query：生成当前 token 的后续表示时，需要当前 Query 去访问历史 K/V，而不是重新计算所有历史位置的 attention 输出。

## 8. 为什么不能只缓存最后一层？

因为新 token 在第一层就需要第一层的历史 K/V；到第二层又需要第二层的历史 K/V。

最后一层的 K/V 是另一阶段的表示，不能直接满足前面各层的计算需求。只保存最后一层，并不能省掉其他层所需历史 K/V 的重算。

可以用一个不完全精确但直观的类比：

> 多道工序分别保留各自的中间结果。下一次处理新增内容时，每道工序复用自己的历史结果，而不是所有工序都拿最终成品当作原料。

## 9. 这和显存、Prefill/Decode 分离有什么关系？

### KV cache 容量与层数有关

对于每层配置相同、使用普通 K/V 存储的全上下文 attention，单条序列的 KV cache 数据量可以粗略估算为：

```text
KV cache 字节数 ≈ 2 × L × T × Hkv × Dhead × b
```

- `2`：分别存储 Key 和 Value。
- `L`：保存 KV cache 的 attention 层数。
- `T`：缓存的 token 数量。
- `Hkv`：每层的 KV head 数量，不一定等于 Query head 数量。
- `Dhead`：每个 KV head 的向量维度，这里假设 K/V 维度相同。
- `b`：每个元素占用的字节数。

例如，假设 32 层、4096 个 token、8 个 KV head、每个 head 128 维、每元素 2 字节：

```text
2 × 32 × 4096 × 8 × 128 × 2 = 536,870,912 字节 = 512 MiB
```

这只是单条序列、未考虑分页对齐和元数据等开销的逻辑数据量，也不包含模型权重。多请求、prefix sharing、缓存量化、滑动窗口以及模型并行切分，都会影响实际显存占用或分布。

### P/D 分离需要衔接各层的缓存

当 prefill 和 decode 在不同 worker 上执行时，decode 端需要能够访问该请求在相关 attention 层的 KV 状态，而不是只拿到最后一层的结果或第一个输出 token。

因此，KV 数据传输或共享访问是 P/D 分离的重要成本。具体实现可以分页、分层、流水化或按并行 rank 切分，并不一定一次性复制一整块连续内存；还需要配套的请求和缓存元数据。

## 10. 常见误解速查

| 说法 | 更准确的理解 |
| --- | --- |
| 32 层就是把同一句话存了 32 遍 | 各层处理相同位置，但保存的是不同阶段、不同参数产生的 K/V |
| 图中每层都写着 Kubernetes，所以内容相同 | 单词只是 token 位置标签，不是实际向量值 |
| 每个单词总是一个 token | 实际划分取决于 tokenizer，教学示意不能当作真实编码 |
| Prefill 并行，所以每个位置都能看到整个 prompt | Causal mask 仍限制每个位置只能看到自己和之前的位置 |
| 只保存最后一层 KV 就够了 | 每层 attention 需要对应层的历史 K/V |
| 有 KV cache 后，新 token 不必经过所有层 | 新 token 仍需要经过各层，只是不必重新处理整个历史前缀 |
| KV cache 是模型权重 | 权重是模型参数；KV cache 是处理具体输入时产生的运行时状态 |
| Layer 和 attention head 是一回事 | Head 位于 attention 层内部，是不同的维度 |

## 11. 适合演讲的中文表述

> 模型里有很多层，每一层都会对上一层的结果继续做处理。所以，同一个 token 在不同层里的表示是不一样的，每层算出来的 key 和 value 也不一样。
>
> Prefill 会把这些结果按层保存下来，这就是 KV cache。到了 decode 阶段，新 token 还是要经过所有层，但每一层都可以直接复用自己之前保存的 key 和 value，不用把整个 prompt 从头再算一遍。
>
> 所以，32 层不是把同一句话存了 32 遍，而是保存了这句话在 32 个不同计算阶段产生的中间结果。

## 参考资料

- [Hugging Face Transformers：How caching works](https://huggingface.co/docs/transformers/main/cache_explanation)：按层缓存 K/V、causal attention 下的复用、缓存更新与张量维度。
- [Attention Is All You Need](https://arxiv.org/abs/1706.03762)：Transformer、scaled dot-product attention 和 multi-head attention 的基础定义。
