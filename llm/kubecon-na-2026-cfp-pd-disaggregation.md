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

### Grocery Stores near Radisson / Radisson 附近步行可达超市

**出发点：Radisson Hotel Salt Lake City Downtown，215 W South Temple。** 以下均为单程步行距离与时间的街区路线估算，**未核实实时步行导航**，不含购物、等红灯或施工绕行；与上方酒店表中的“到会场距离”不同。地址及常规营业时间于 **2026-11-05** 核对门店官网，均为盐湖城当地时间；临时调整请出发前再次确认。

| 超市 | 地址 | 单程步行距离（估算） | 单程步行时间（估算） | 官网公布营业时间 | 适合买什么 |
|---|---|---|---|---|---|
| **The Store — The Gateway** | **90 S Rio Grande, Salt Lake City, UT 84101** | **约 0.8–1.0 km** | **约 10–15 分钟** | **周一至周六 07:00–22:00；周日 08:00–20:00** | 较小型精品超市，适合简单食品杂货、零食饮料及路餐补给；当天熟食供应以门店为准 |
| **Harmons — City Creek Center** | **135 E 100 S, Salt Lake City, UT 84111** | **约 1.1–1.3 km** | **约 15–20 分钟** | **每天 07:00–22:00，含周日** | 较完整的超市，适合购买水果、面包、酸奶、饮料和徒步零食，一次买齐早餐与路餐 |

- **只买几样零食饮料：**优先考虑较近的 The Store；**准备徒步补给或集中采购：**建议多走几分钟到 Harmons。若准备 11/8 徒步早餐与路餐，建议前一天买齐。
- **The Store 步行导航：**[Radisson → The Store Gateway（Google Maps）](https://www.google.com/maps/dir/?api=1&origin=Radisson+Hotel+Salt+Lake+City+Downtown&destination=The+Store+90+S+Rio+Grande+St+Salt+Lake+City&travelmode=walking)。[门店官网与营业时间](https://www.thestorefinefoods.com/thestore)，电话 **385-213-7900**。
- **Harmons 步行导航：**[Radisson → Harmons City Creek（Google Maps）](https://www.google.com/maps/dir/?api=1&origin=Radisson+Hotel+Salt+Lake+City+Downtown&destination=Harmons+135+E+100+S+Salt+Lake+City&travelmode=walking)。[门店官网与营业时间](https://www.harmonsgrocery.com/locations/city-creek-center)，电话 **801-428-0366**。
- **周日提醒：**两家超市官网均列出周日营业，但 The Store 周日关门较早；不要将其他商场或餐厅的周日营业安排直接套用于这两家门店。

### Korean Food near Radisson / Radisson 出发的韩餐选择

**出发点：Radisson Hotel Salt Lake City Downtown，215 W South Temple。** 步行范围内主要是韩式快餐；Stun Cube 和 Baek Ri Hyang 位于酒店以南，**不属于酒店附近步行可达餐厅**。以下交通时间均为粗估，不是实时导航；轻轨候车、换乘及拥堵另计。地址信息于 **2026-11-05** 核对，下列来源类型分别注明。

| 餐厅 | 地址 | 菜式与适合场景 | 从酒店怎么去 |
|---|---|---|---|
| **Cupbop Downtown** | **45 E Broadway（300 S）, Salt Lake City, UT 84111** | 韩式快餐饭碗，烤肉／鸡肉搭配米饭、粉丝和酱汁；不是桌边韩式烤肉店。适合就近简单吃一顿 | **步行约 20–25 分钟**；或步行至 **Temple Square Station**，乘向南的 TRAX 蓝线或绿线至 **Gallivan Plaza**，再步行几分钟 |
| **Stun Cube** | **2732 S State St, South Salt Lake, UT 84115**（官网地址） | 韩式家常便当 **dosirak**，米饭搭配主菜和小菜；菜单以官网点餐页为准 | 不建议步行；打车可先预留 **约 15–25 分钟**，具体以当时导航为准 |
| **Baek Ri Hyang（百里香）** | **3390 S State St #31, South Salt Lake, UT 84115**（第三方目录交叉核对，非已验证官网） | 韩式中华料理，可关注 **jajangmyeon（炸酱面）、jjamppong（辣海鲜面）、tangsuyuk（糖醋肉）**；当天供应需确认 | 不建议步行；打车可先预留 **约 15–25 分钟**，具体以当时导航为准 |

- **Cupbop：**[品牌官网](https://www.cupbop.com/)；[Downtown 门店地址及点餐页](https://order.online/en-US/store/CupBop-Downtown-491273)。与 Ramen 930 位于同一地址，但不要把另一品牌的营业时间直接视为 Cupbop 的营业时间；本次未确认 Cupbop Downtown 的官方营业时段，出发前查看门店页面。[从酒店步行导航](https://www.google.com/maps/dir/?api=1&origin=Radisson+Hotel+Salt+Lake+City+Downtown&destination=Cupbop+45+E+Broadway+Salt+Lake+City&travelmode=walking)。
- **Stun Cube：**[官网与菜单](https://www.stuncube.com/)，电话 **801-419-0082**；官网公布 **周一至周六 11:00–20:00，周日休息**。请使用官网当前列出的 **2732 S State St** 导航。[驾车导航](https://www.google.com/maps/dir/?api=1&origin=Radisson+Hotel+Salt+Lake+City+Downtown&destination=Stun+Cube+2732+S+State+St+South+Salt+Lake&travelmode=driving)。
- **Baek Ri Hyang：**[FindRice 门店资料](https://www.findrice.com/salt-lake-city/store/95)及[另一门店目录](https://usarestaurants.info/explore/united-states/utah/salt-lake-county/south-salt-lake/baek-ri-hyang-801-883-9693.htm)均列出 **3390 S State St #31**；目录联系电话 **801-883-9693**。本次未验证到可用官网或官方营业时间，建议先电话确认仍在营业、当天时段及地址。[驾车导航](https://www.google.com/maps/dir/?api=1&origin=Radisson+Hotel+Salt+Lake+City+Downtown&destination=Baek+Ri+Hyang+3390+S+State+St+31+South+Salt+Lake&travelmode=driving)。
- **选择建议：**图方便选 **Cupbop**；想吃韩式家常便当选 **Stun Cube**；想吃韩式炸酱面或辣海鲜面可考虑 **Baek Ri Hyang**，但先确认营业。公共交通以当天 Transit App／Google Maps 为准，尤其注意周日与晚间班次；是否免费乘车以 [UTA Free Fare Zone 官方范围](https://www.rideuta.com/Fares-And-Passes/Individual-Fares/Free-Fare-Zone)判断。

### NBA Games in Salt Lake City / 盐湖城 NBA 观赛参考（2026-11-07 至 2026-11-20）

**查询范围：2026 年 11 月 7 日至 11 月 20 日，含首尾日期。** 根据 2026-10-24 查询到的公开赛程和票务信息，这段时间盐湖城有以下 **4 场犹他爵士（Utah Jazz）主场比赛**，均在 **Delta Center** 举行。

| 日期 / Date | 星期 / Day | 比赛 / Matchup | 开赛时间 / Tip-off（盐湖城当地时间） | 备注 / Notes |
|---|---|---|---|---|
| **2026-11-10** | 周二 / Tuesday | 爵士 vs 迈阿密热火 / Utah Jazz vs. Miami Heat | **19:00** | 常规赛 / Regular season |
| **2026-11-11** | 周三 / Wednesday | 爵士 vs 奥兰多魔术 / Utah Jazz vs. Orlando Magic | **19:00** | 常规赛 / Regular season |
| **2026-11-15** | 周日 / Sunday | 爵士 vs 圣安东尼奥马刺 / Utah Jazz vs. San Antonio Spurs | **15:00** | 周末下午场 / Sunday afternoon |
| **2026-11-20** | 周五 / Friday | 爵士 vs 菲尼克斯太阳 / Utah Jazz vs. Phoenix Suns | **19:30** | **NBA Cup 小组赛 / Group play** |

**场馆 / Venue:** Delta Center<br>
**地址 / Address:** 301 West South Temple, Salt Lake City, UT 84101, USA

**时区提醒 / Time zone:** 表中均为盐湖城当地时间，**不是北京时间**。这段时间盐湖城使用 **MST（UTC−7）**，比北京时间（UTC+8）**晚 15 小时**。例如当地 11 月 10 日 19:00 对应北京时间 11 月 11 日 10:00。

**选择建议 / Suggestions:**

- 想周末看球，可优先考虑 **11 月 15 日（周日）15:00 的马刺场**。
- 如果 **11 月 20 日**仍在盐湖城，也可考虑当晚 **19:30 的太阳 NBA Cup 场**。
- **11 月 10 日、11 日**是晚场，安排观赛前请核对自己的会议、晚间活动及交通计划。

**赛程来源与购票入口 / Schedule sources and tickets:**

- [Utah Jazz 官方赛程及购票入口 / Official schedule](https://www.nba.com/jazz/schedule)
- [American Arenas — Utah Jazz 2026–2027 赛程列表](https://americanarenas.com/sports/nba/utah-jazz/schedule/)（本表的比赛日期、场馆及当地开赛时间来源）
- [11 月 10 日：热火客场对爵士 / Heat at Jazz — StubHub](https://www.stubhub.com/utah-jazz-salt-lake-city-tickets-11-10-2026/event/161731659/)
- [11 月 20 日：太阳客场对爵士 / Suns at Jazz, NBA Cup — StubHub](https://www.stubhub.com/utah-jazz-salt-lake-city-tickets-11-20-2026/event/161731648/)

> 信息整理日期：**2026-10-24**。比赛日期、开赛时间及票务库存可能调整；**购票前请再次以爵士官方赛程和实际票务页面为准**。StubHub 为第三方票务平台，本表不代表票价或余票保证。
