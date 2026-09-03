# KubeCon North America 2026 — CFP Submission

---

## Title

**Prefill Here, Decode There: Kubernetes-Native LLM Inference Disaggregation with KAITO and llm-d**

<details>
<summary>Alternate titles considered</summary>

- Scaling Disaggregated LLM Inference on Kubernetes: KAITO + llm-d + Gateway API
- One CRD, Two GPU Pools: Disaggregated LLM Inference with KAITO
- Split the GPU, Not the YAML: P/D Disaggregated Inference on Kubernetes
- Beyond Single-Pod Inference: Building a P/D Disaggregation Stack with Gateway API, llm-d, and KEDA
- Your LLM Prefill Is Starving Your Decode: Fixing It with KAITO and llm-d on Kubernetes
- KAITO + llm-d: Declarative Prefill/Decode Disaggregation on Kubernetes
- From 20 Lines of YAML to Disaggregated DeepSeek: A KAITO + llm-d Journey
</details>

---

## Session Type

Conference Session (35 min)

## Track

AI + ML + Intelligent Apps / Runtime

## Level

Intermediate

---

## Abstract (max 900 characters)

LLM inference has two phases with very different resource profiles: prefill is compute-bound and latency-sensitive, decode is memory-bandwidth-bound and throughput-sensitive. Running both on the same GPU pool forces a compromise — over-provisioning for prefill spikes wastes decode capacity, and vice versa.

P/D disaggregation fixes this, but existing approaches (NVIDIA Dynamo, llm-d standalone) require extensive manual wiring: topology-aware routing, KV cache transfer protocols, sidecar lifecycle management, and per-role autoscaling. KAITO introduces MultiRoleInference — a higher-level Kubernetes abstraction that composes llm-d's routing and Gateway API Inference Extension into a single declarative CRD.

We'll present the motivation for this layered approach vs. Dynamo/llm-d alone, share eval data comparing P/D vs. colocated serving (TTFT, throughput, GPU utilization), and demonstrate KEDA-driven autoscaling for each role independently.

---

## Description (max 1000 characters)

The problem: P/D disaggregation improves LLM serving efficiency by 30-60% on prefill-heavy workloads, but infrastructure complexity is brutal — routing sidecars, NIXL KV transfer, ZMQ discovery, port management, scheduling profiles, and independent autoscaling all need correct orchestration.

Existing solutions: NVIDIA Dynamo provides disaggregation but is tightly coupled to NVIDIA's stack, not Kubernetes-native. llm-d offers Kubernetes-native P/D routing via Gateway API but requires manual StatefulSet config, sidecar injection, and env var plumbing.

KAITO's MultiRoleInference CRD bridges this gap: a declarative layer orchestrating llm-d components automatically. One CRD generates prefill/decode StatefulSets with correct port assignments, NIXL env vars, decode-only sidecar injection, InferencePool with proper targetPort, EPP plugin chain, and KEDA ScaledObjects per role.

We'll show eval data: TTFT reduction, throughput gains, and autoscaling behavior under mixed workloads.

---

## Benefits to the Ecosystem

Attendees will learn:

1. **A layered abstraction for complex inference topologies** — How KAITO's MultiRoleInference CRD composes Gateway API InferencePool, llm-d EPP plugins, and vLLM NIXL into one declarative interface. Why this matters as topologies grow (E/P/D, speculative decoding, MoE).

2. **When to use P/D disaggregation** — Eval data showing TTFT reduction, throughput gains, GPU utilization improvements under different workload profiles, and break-even analysis by prompt length.

3. **How to autoscale P/D independently** — KEDA with role-specific metrics: prefill scales on queue depth, decode on KV-cache utilization. Example of asymmetric scaling under bursty traffic.

4. **KAITO vs Dynamo vs llm-d standalone** — Dynamo is Python-native/NVIDIA-coupled; llm-d is K8s-native but manual; KAITO adds a declarative CRD layer with built-in KEDA autoscaling, vendor-neutral GPU support, and single-CRD multi-model management.

5. **Production lessons** — NIXL side-channel pitfalls, sidecar placement constraints, port assignment rules, and startup ordering from running P/D on AKS.

All components are open source: KAITO (CNCF Sandbox), llm-d, Gateway API Inference Extension (K8s SIG), KEDA (CNCF Graduated).

---

## Talk Outline (35 min)

1. **The Problem** (5 min)
   - Why prefill and decode fight for the same GPU
   - Real production traces showing interference patterns
   - Cost of over-provisioning vs. latency degradation

2. **Landscape: How Others Solve It** (5 min)
   - NVIDIA Dynamo: Python-native, tightly coupled
   - llm-d standalone: K8s-native but manual
   - Why Kubernetes needs a higher-level abstraction

3. **KAITO MultiRoleInference Design** (8 min)
   - The CRD spec and what it generates
   - How it composes llm-d, Gateway API, and NIXL
   - Key design decisions: decode-only sidecar, port conventions, label contracts

4. **Live Demo** (10 min)
   - Deploy a model with P/D disaggregation (single YAML)
   - Show NIXL KV transfer in action (real-time metrics)
   - Trigger load spike → watch KEDA scale prefill independently
   - Compare latency: P/D vs. colocated baseline

5. **Eval Data & When to Use P/D** (5 min)
   - TTFT, throughput, utilization benchmarks
   - Break-even analysis by prompt length
   - Cost comparison (fewer total GPUs needed)

6. **What's Next** (2 min)
   - E/P/D (multimodal encode disaggregation)
   - Speculative decoding integration
   - Cross-node RDMA optimization

---

## Speaker Bio

**Andy Zhang**

**Linbo He**

---

## Tags / Keywords

`kubernetes`, `llm-inference`, `gpu`, `prefill-decode-disaggregation`, `gateway-api`, `kaito`, `llm-d`, `vllm`, `kv-cache`, `autoscaling`, `keda`, `cncf`, `nixl`, `dynamo`

---

## References

- KAITO project: https://github.com/kaito-project/kaito
- MultiRoleInference design: https://github.com/kaito-project/kaito/pull/1991
- llm-d inference scheduler: https://github.com/llm-d/llm-d-inference-scheduler
- llm-d disaggregation docs: https://github.com/llm-d/llm-d-router/blob/main/docs/disaggregation.md
- Gateway API Inference Extension: https://github.com/kubernetes-sigs/gateway-api-inference-extension
- KEDA KAITO scaler: https://github.com/kaito-project/keda-kaito-scaler
- NVIDIA Dynamo: https://github.com/ai-dynamo/dynamo
- NIXL (NVIDIA Inference Xfer Library): https://github.com/ai-dynamo/nixl
- P/D working config (our verified setup): https://github.com/andyzhangx/demo/blob/master/llm/pd-disaggregation/kaito/pd-working-config.md

---

## Travel / Logistics

**Event:** KubeCon + CloudNativeCon North America 2026
**Dates:** November 9–12, 2026
**Venue:** [Salt Palace Convention Center](https://www.visitsaltlake.com/salt-palace-convention-center/attend/), 90 South West Temple, Salt Lake City, UT 84101

### Official Schedule Links

- **CNCF-hosted Co-located Schedule:** <https://events.linuxfoundation.org/kubecon-cloudnativecon-north-america/co-located-events/cncf-hosted-co-located-schedule/>
- **Main Conference Schedule:** <https://events.linuxfoundation.org/kubecon-cloudnativecon-north-america/program/schedule/>

### Official Room Block Hotels

All hotels below are part of the official KubeCon NA 2026 room block (discounted rates) and are within walking distance of the Salt Palace Convention Center. Taxes ~17.52% unless noted. Book early — room blocks close mid-to-late October 2026.

| Hotel | Stars | Rate/night | Distance | Walk | Notes |
|---|---|---|---|---|---|
| [Hyatt Regency Salt Lake City](https://www.hyatt.com/hyatt-regency/en-US/slcrs-hyatt-regency-salt-lake-city)<br>盐湖城凯悦酒店 | ★★★★ | $265+ | 0.0 mi | 2 min | Adjacent to venue — most convenient<br>紧邻会场 — 最方便 |
| [Hilton Salt Lake City Center](https://www.hilton.com/en/hotels/slccchh-hilton-salt-lake-city-center/)<br>盐湖城中心希尔顿酒店 | ★★★★ | $259+ | 0.1 mi | 3 min | Right next door<br>就在会场旁边 |
| [Salt Lake Marriott Downtown at City Creek](https://www.marriott.com/en-us/hotels/slcut-salt-lake-marriott-downtown-at-city-creek/overview)<br>盐湖城市溪万豪酒店 | ★★★★ | $259+ | 0.2 mi | 2 min | Very close, flexible cancellation<br>非常近，取消政策灵活 |
| [Kimpton Hotel Monaco](https://www.monaco-saltlakecity.com/)<br>金普顿摩纳哥酒店 | ★★★★ | $224+ | 0.3 mi | 3 min | Boutique; 24h cancellation policy<br>精品酒店；24 小时取消政策 |
| [Hyatt Place Salt Lake City/Downtown/The Gateway](https://www.hyatt.com/hyatt-place/en-US/slczd-hyatt-place-salt-lake-city-downtown-the-gateway)<br>盐湖城市中心 Gateway 凯悦嘉轩 | ★★★ | $215+ | 0.3 mi | 8 min | **Includes breakfast**<br>**含早餐** |
| [Salt Lake Marriott City Center](https://www.marriott.com/en-us/hotels/slccc-salt-lake-city-marriott-city-center/overview)<br>盐湖城市中心万豪酒店 | ★★★★ | $249+ | 0.4 mi | 9 min | Solid four-star option<br>可靠的四星选择 |
| [Element Salt Lake City Downtown](https://www.marriott.com/en-us/hotels/slcel-element-salt-lake-city-downtown/overview)<br>盐湖城市中心雅乐轩 Element | ★★★ | $209+ | ~0.4 mi | ~10 min | **Includes breakfast**; extended-stay style<br>**含早餐**；长住型酒店 |
| [The Little America Hotel](https://saltlake.littleamerica.com/)<br>小美洲酒店 | ★★★★ | $219+ | 0.7 mi | 16 min | Classic SLC property, large rooms<br>盐湖城经典老牌酒店，房间宽敞 |
| [DoubleTree by Hilton Downtown](https://www.hilton.com/en/hotels/slcwsdt-doubletree-suites-salt-lake-city-downtown/)<br>市中心希尔顿逸林酒店 | ★★★ | $234+ | 0.7 mi | 16 min | 15.52% tax (lower)<br>税率较低 (15.52%) |

### Additional Nearby Hotels (not in official room block / 非官方协议酒店)

These hotels are **not** part of the KubeCon official room block, so you won't get the conference discount — but several are actually **closer to the venue** than some official block properties. Book via each hotel's website, Booking.com, Expedia, etc. Prices fluctuate and rooms may sell out earlier, so book ASAP if the official block is full or you prefer these properties.

以下酒店**不在** KubeCon 官方协议价名单中，所以拿不到大会折扣价，但其中不少地理位置甚至比官方名单里的酒店更近。可直接通过酒店官网或 Booking/Expedia 等平台预订。价格会波动，房间也可能更早售完，建议尽早预订。

| Hotel | Stars | Distance | Walk | Notes |
|---|---|---|---|---|
| [Radisson Hotel Salt Lake City Downtown](https://www.radissonhotelsamericas.com/en-us/hotels/radisson-salt-lake-city)<br>盐湖城市中心丽笙酒店 | ★★★ | 0.1 mi | 2 min | Steps from convention center entrance; Copper Canyon restaurant on-site; 15 meeting rooms<br>紧邻会场入口；含 Copper Canyon 餐厅；15 间会议室 |
| [Le Méridien Salt Lake City Downtown](https://www.marriott.com/en-us/hotels/slcmd-le-meridien-salt-lake-city-downtown/overview/)<br>盐湖城市中心艾美酒店 | ★★★★ | 0.2 mi | 3 min | Boutique design, 144 rooms; outdoor pool; Adelaide French-inspired restaurant<br>精品设计，144 间客房；室外泳池；Adelaide 法式风格餐厅 |
| [Hyatt House Salt Lake City/Downtown](https://www.hyatt.com/hyatt-house/en-US/slcxd-hyatt-house-salt-lake-city-downtown)<br>盐湖城市中心凯悦嘉寓 | ★★★ | 0.2 mi | 3 min | All-suite with in-room kitchens; **free breakfast**; H Bar in lobby<br>全套房带厨房；**含免费早餐**；大堂 H Bar |
| [Holiday Inn Express Salt Lake City Downtown](https://www.ihg.com/holidayinnexpress/hotels/us/en/salt-lake-city/slcew/hoteldetail)<br>盐湖城市中心智选假日酒店 | ★★★ | 0.2 mi | 3 min | **Best value pick**; free hot breakfast; indoor pool, hot tub, sauna; 2,400+ reviews<br>**性价比首选**；免费热早餐；室内泳池、热水浴缸、桑拿；2400+ 评论 |
| [AC Hotel by Marriott Salt Lake City Downtown](https://www.marriott.com/en-us/hotels/slcak-ac-hotel-salt-lake-city-downtown/overview/)<br>盐湖城市中心 AC 万豪酒店 | ★★★★ | 0.3 mi | 5 min | Modern boutique; Marriott Bonvoy; European-inspired design<br>现代精品风格；Marriott Bonvoy 积分；欧式设计 |
| [Courtyard by Marriott Salt Lake City Downtown](https://www.marriott.com/en-us/hotels/slcdt-courtyard-salt-lake-city-downtown/overview/)<br>盐湖城市中心万怡酒店 | ★★★ | 0.3 mi | 6 min | Reliable business-class standard; good value<br>可靠的商务级酒店；性价比不错 |
| [Kimpton Grand Hotel Salt Lake](https://www.grandhotelsaltlake.com/)<br>盐湖城金普顿豪华酒店 | ★★★★ | ~0.6 mi | ~12 min | Recently renovated; near Delta Center<br>近期翻新；靠近 Delta Center |
| [Sheraton Salt Lake City Hotel](https://www.marriott.com/en-us/hotels/slcsi-sheraton-salt-lake-city-hotel/overview/)<br>盐湖城喜来登酒店 | ★★★★ | 0.8 mi | 16 min | Marriott portfolio; business-focused<br>万豪旗下；商务定位 |

**💡 Trade-off / 权衡：**

- ✅ Better location or unique style (Radisson, Le Méridien, Hyatt House, AC — all ≤ 0.3 mi)<br>更好的位置或独特风格（Radisson、Le Méridien、Hyatt House、AC — 均在 0.3 mi 内）
- ✅ Not bound by official block cutoff dates<br>不受官方 room block cutoff 时间限制
- ⚠️ No conference discount — compare final price with the official rate before deciding<br>没有大会折扣 — 下单前请与官方协议价比较
- ⚠️ May sell out earlier during peak conference week<br>大会高峰期可能更早售罄

### Recommendations

**🏃 Closest to venue / 距离会场最近:**
- Hyatt Regency (0.0 mi, skybridge to Salt Palace) — official block
- Radisson (0.1 mi) — non-block
- Salt Lake Marriott Downtown at City Creek (0.1 mi) — official block

**💰 Best value / 性价比首选:**
- Holiday Inn Express (~$150–200, 0.2 mi, free breakfast) — non-block
- Element ($209, official block, free breakfast)
- Hyatt Place ($215, official block, free breakfast)

**💎 Design / boutique experience / 精品体验:**
- Le Méridien (0.2 mi, non-block) — modern boutique
- Kimpton Hotel Monaco (0.3 mi, official block, 24h cancellation)
- Kimpton Grand Hotel (0.6 mi, non-block) — recently renovated

**🍳 Long-stay / kitchen + breakfast / 长住带厨房+早餐:**
- Hyatt House (0.2 mi, non-block) — full kitchen, free breakfast
- Element (0.4 mi, official block) — full kitchen, free breakfast

**✨ Most flexible cancellation / 最灵活取消政策:**
- Kimpton Hotel Monaco (24h)
- Salt Lake Marriott Downtown at City Creek (24h)

**🎯 Loyalty program tip / 积分党提示:** Marriott Bonvoy (7 properties here), Hilton Honors (2), World of Hyatt (3), IHG One Rewards (Holiday Inn Express), Radisson Rewards (1).

Official venue + travel page (booking links, room block cutoffs): <https://events.linuxfoundation.org/kubecon-cloudnativecon-north-america/attend/venue-travel/>
