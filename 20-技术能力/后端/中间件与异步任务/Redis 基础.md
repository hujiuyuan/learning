---
type: 基础能力
通用技能: 中间件与异步任务
技能点: Redis
域: 后端
证据: 学习中
---

# Redis 基础

技能点：[[Redis]] · 定位：基础知识挂载页

**一句话**：Redis 基础题的分类索引。这里回答「应该会什么」，不冒充「我做过什么」；做过的事仍记在实践卡。

## 怎么用

- 自测：看每一块的「要能回答」，能用自己的话讲清楚才算过。
- 挂笔记：新写一篇八股文，在对应块的「笔记」后加 `笔记名`，笔记里链回本页。
- 分边界：原理和机制放这里；具体故障、排查过程、修复方案放场景/实践卡。

## 1. 数据结构

**一句话**：String、Hash、List、Set、ZSet 是五种基础结构，底层由 SDS、dict、ziplist/listpack、skiplist 等编码实现；按访问模式选结构，不要所有东西都塞 String。

要能回答：

- 五种基础结构的典型使用场景？
- String 的 SDS 和 C 字符串有什么区别？
- Hash 的底层编码什么时候从 listpack 转 dict？
- ZSet 为什么用跳表？和平衡树比有什么取舍？
- Bitmap、HyperLogLog、GEO、Stream 分别适合什么？
- 大 key 怎么定义？有什么危害？

**笔记**：

- String 适合单值/计数/位图；Hash 适合对象字段；List 适合队列/栈（但阻塞队列要用 Stream 或专业 MQ）；Set 适合去重/交并差；ZSet 适合排行榜/延迟队列（score 当时间戳）。
- SDS 在 C 字符串外增加了长度和剩余空间：`strlen` O(1)、二进制安全（可以存 `\0`）、追加前检查扩容、避免缓冲区溢出。C 字符串靠 `\0` 结尾，不能存二进制，长度要遍历。
- Hash 默认 listpack（紧凑、连续内存），字段数或单个 value 超过 `hash-max-listpack-entries`/`hash-max-listpack-value` 后转 dict（哈希表）；ZSet 默认 listpack，超过 `zset-max-listpack-entries`/`zset-max-listpack-value` 后转 skiplist + dict。阈值是为了在「小对象省内存」和「大对象 O(1)/O(log N)」之间取平衡。
- ZSet 用跳表而不是平衡树：实现简单、范围查询天然有序、插入删除不需要旋转/再平衡；代价是指针多、内存占用比紧凑结构高。Redis 单线程，简单可维护比极致省内存更重要。
- Bitmap 适合签到/布尔标记；HyperLogLog 适合基数估算（有误差、不存原值）；GEO 底层是 ZSet + geohash；Stream 适合消息流/消费组。大 key 没有绝对阈值，通常 string >10KB、集合元素 >5000 就要警惕：它会阻塞单线程、占网络带宽、造成内存倾斜，删除用 `UNLINK` 异步释放。

## 2. 缓存模式

**一句话**：Cache-Aside 是最常用模式：读时先查缓存、未命中回源并回填；写时更新 DB 再删缓存，不能先删缓存再写 DB。

要能回答：

- Cache-Aside、Read-Through、Write-Through、Write-Behind 的区别？
- 为什么是「删缓存」而不是「更新缓存」？
- 先删缓存再写 DB 会有什么并发问题？延迟双删解决什么？
- 缓存穿透、击穿、雪崩分别是什么？怎么防？
- 缓存和数据库不一致的窗口怎么收敛？
- 热点 key 怎么发现和处理？

关联：[[Redis]]

**笔记**：

- Cache-Aside：应用自己读写缓存和 DB；Read-Through：缓存组件负责回源；Write-Through：写穿透，缓存和 DB 同步写；Write-Behind：先写缓存、异步刷 DB，吞吐高但可能丢数据。业务系统最常用 Cache-Aside，因为控制权在应用。
- 写时「删缓存」而不是「更新缓存」：更新缓存需要知道新值、可能写入一个稍后又被别的事务覆盖的旧值；删除是幂等的，下次读自然回填。并发写时仍可能不一致，所以删除后要配合重试/TTL/订阅 binlog。
- 先删缓存再写 DB：删完后、DB 写完前，另一个读请求会把旧值回填，之后 DB 新值就被旧缓存盖住。延迟双删是「删缓存 → 写 DB → 延迟再删一次」，只能降低概率，不能证明一致；更强的是写后删 + 重试 + TTL 兜底。
- 穿透：查不存在的数据，缓存不命中每次都打 DB；用空值缓存（短 TTL）、布隆过滤器、参数校验。击穿：热点 key 过期瞬间大量请求打 DB；用互斥重建/逻辑过期。雪崩：大量 key 同时过期或 Redis 挂；给 TTL 加随机抖动、多级缓存、限流降级。
- 不一致窗口的收敛：先写 DB 再删缓存、删除失败重试、binlog 订阅补偿、TTL 兜底；强一致场景不要用缓存，或接受「读旧值」的业务语义。
- 热点 key：监控 `hotkeys`/代理层统计；本地缓存、读写分离、key 拆分（把热点分散到多个副本）、限流。热点 key 的发现比修复更难，先有监控。

## 3. 过期与淘汰

**一句话**：过期策略是惰性删除 + 定期删除；内存满时按 `maxmemory-policy` 淘汰，淘汰策略选错会删掉不该删的 key。

要能回答：

- Redis 的过期键怎么删除？为什么不用定时器逐个删？
- `volatile-lru`、`allkeys-lru`、`volatile-ttl`、`noeviction` 的区别？
- LRU 和 LFU 的区别？Redis 的近似 LRU 怎么实现？
- 内存碎片怎么产生？`MEMORY PURGE` 做什么？
- 过期 key 太多会阻塞主线程吗？
- 如何估算 Redis 内存？

**笔记**：

- 惰性删除：访问 key 时检查过期；定期删除：后台周期性随机抽样过期字典，删掉过期 key。不用「每个 key 一个定时器」是因为百万级 key 的定时器开销太大，而且单线程会被定时任务拖住。
- `volatile-*` 只淘汰设置了过期时间的 key；`allkeys-*` 淘汰所有 key；`noeviction` 不淘汰，写请求返回 OOM。缓存场景常用 `allkeys-lru`/`allkeys-lfu`；如果 Redis 里混了「不能丢」的数据，必须分开实例，不能靠策略猜。
- LRU 看「最近访问」，LFU 看「访问频率」；Redis 的 LRU 是近似实现：每个对象记录最近访问时间，淘汰时随机采样几个 key 选最久没用的，不是全局链表。LFU 用计数器 + 衰减，避免偶发访问把冷 key 留住。
- 内存碎片来自频繁分配/释放不同大小的对象；`MEMORY PURGE` 让分配器把空闲页还给 OS，但会阻塞；`activedefrag` 可以后台整理。碎片率高不一定是泄漏，先看 `mem_fragmentation_ratio`。
- 过期 key 太多会拖慢主线程：定期删除是分批抽样，但大量 key 同时过期仍可能造成延迟尖峰；TTL 加随机值可以打散。
- 估算内存：key 本身 + value + dict entry + expires 字典 + 对象头/编码开销；用 `MEMORY USAGE key` 看单个 key，用 `INFO memory` 看总量，按「样本 × 数量」估，不要只算 value 字节数。

## 4. 持久化

**一句话**：RDB 是快照，AOF 是追加日志；RDB 恢复快但可能丢数据，AOF 更持久但文件大、恢复慢；生产常用混合持久化。

要能回答：

- RDB 的 `save` 和 `bgsave` 有什么区别？fork 的代价？
- AOF 的 `always`、`everysec`、`no` 分别丢多少数据？
- AOF 重写解决什么问题？重写期间的新写入怎么办？
- 混合持久化是什么？
- 主从复制和持久化怎么配合？
- 宕机后怎么判断能恢复到哪里？

**笔记**：

- `save` 在主线程执行，会阻塞；`bgsave` fork 子进程写快照，主线程继续服务。fork 的代价是复制页表，内存越大越慢；写时复制（COW）让父子共享页，写多的实例内存可能翻倍。
- AOF `always` 每条命令 fsync，最安全最慢；`everysec` 每秒 fsync，最多丢 1 秒；`no` 交给 OS，可能丢更多。生产常用 `everysec`。
- AOF 重写把「多次写同一 key」压成最终状态，减小文件；重写期间新写入同时进旧 AOF 和重写缓冲区，重写完成后追加，避免丢命令。
- 混合持久化：RDB 存全量快照，AOF 存快照后的增量；重启先加载 RDB 再重放 AOF，兼顾恢复速度和数据完整性。
- 主从复制和持久化配合：从库也可以开持久化；主库宕机后，哨兵提升从库，但异步复制可能丢最后一段。持久化不能替代复制，复制也不能替代备份。
- 宕机恢复点：看最后一次 RDB 时间 + AOF 最后一条命令；`INFO persistence` 的 `rdb_last_save_time`、`aof_last_write_status`；如果 AOF 关闭，只能恢复到上一次快照。

## 5. 复制与集群

**一句话**：主从复制异步、哨兵做故障转移、Cluster 按槽分片；复制延迟和脑裂是分布式场景的核心风险。

要能回答：

- 主从复制的全量同步和增量同步流程？
- 复制缓冲区（repl backlog）有什么用？
- 哨兵怎么判断主库下线？主观下线和客观下线的区别？
- Cluster 的 16384 个槽怎么分配？MOVED 和 ASK 重定向的区别？
- Cluster 下多 key 操作有什么限制？
- 脑裂时数据会怎样？怎么降低风险？

**笔记**：

- 全量同步：从库发 `PSYNC`，主库 `BGSAVE` 生成 RDB 发给从库，期间的新写命令放复制缓冲区；从库加载 RDB 后重放缓冲。增量同步：从库带 `replid` + offset，主库从 backlog 里补发缺失部分；backlog 太小会退化成全量。
- 哨兵：主观下线是单个哨兵认为主库失联；客观下线是达到 quorum 的哨兵都认为失联；然后选举 leader 哨兵执行故障转移，选新主、让其他从库复制新主。
- Cluster 把 key 按 CRC16 映射到 16384 个槽；MOVED 表示「这个槽永久归另一个节点」，ASK 表示「正在迁移，这次去目标节点问」。多 key 操作要求 key 在同一个槽，用 hash tag `{user:1}` 可以把相关 key 绑在一起。
- 脑裂：主库和哨兵/其他节点网络分区，客户端还在往旧主写，新主已经选出；恢复后旧主的数据可能被丢弃。降低风险：`min-replicas-to-write` + `min-replicas-max-lag` 让主库在没有足够从库确认时拒绝写；但会牺牲可用性。
- 复制是异步的：主库提交成功不代表从库收到；故障转移可能丢最后一段。需要强一致就要接受同步复制/多数派确认的延迟，Redis 原生不提供强一致。

## 6. 分布式锁

**一句话**：锁要同时满足互斥、过期、续期、误删保护；`SET key value NX EX` 是起点，解锁要用 Lua 比对 value。

要能回答：

- `SET NX EX` 怎么实现锁？为什么 value 要放唯一标识？
- 锁过期了业务没执行完怎么办？看门狗怎么续期？
- 解锁为什么要用 Lua？不用会误删什么？
- Redisson 的 `RLock` 怎么实现可重入和续期？
- Redis 主从切换时锁会丢吗？RedLock 解决了什么、没解决什么？
- 锁等待、锁超时、锁重入分别怎么处理？

关联：[[Redisson]]、[[定时任务多副本锁]]

**笔记**：

- `SET key uniqueValue NX EX ttl`：NX 保证只有一个人拿到，EX 防止死锁，uniqueValue 标识持有者。解锁必须「比较 value 再删」，否则 A 的锁过期、B 拿到锁，A 执行完把 B 的锁删了。
- 业务没执行完锁过期：看门狗定时续期（Redisson 默认 30 秒锁、10 秒续一次）；续期线程挂了/进程 pause，锁仍可能过期。续期不是无限安全，业务要有幂等/版本号兜底。
- 解锁 Lua：`if redis.call('get',KEYS[1]) == ARGV[1] then return redis.call('del',KEYS[1]) else return 0 end`，保证「比较 + 删除」原子。
- Redisson `RLock` 用 Hash 存「持有者 + 重入次数」，加锁/解锁用 Lua；可重入、看门狗、等待时间/租约时间都可配。
- Redis 主从切换会丢锁：主库写入锁后还没同步到从库就宕机，从库提升后锁消失，另一个客户端能拿到。RedLock 向多个独立 Redis 加锁，降低单点风险，但仍受时钟漂移、进程 pause、网络延迟影响；强一致场景要用 ZooKeeper/etcd 或数据库唯一约束，不能把 Redis 锁当强一致。
- 锁等待用 `tryLock(waitTime, leaseTime, unit)`；leaseTime 为 -1 启用看门狗；重入靠 Hash 计数。抢不到锁是「跳过」还是「排队」，由业务定，不要默认自旋。

## 7. Lua、Pipeline 与事务

**一句话**：Lua 保证一段脚本原子执行；Pipeline 减少网络往返但不保证原子；Redis 事务（MULTI/EXEC）只保证命令一起执行，不保证回滚。

要能回答：

- Lua 脚本为什么原子？执行时间过长会怎样？
- Pipeline 和事务的区别？
- `MULTI`/`EXEC` 中某条命令失败，其他命令会回滚吗？
- `WATCH` 怎么实现乐观锁？
- Lua 脚本怎么传参、怎么返回复杂类型？
- 集群模式下 Lua 有什么限制？

**笔记**：

- Redis 单线程执行命令，Lua 脚本作为一个整体执行，中间不会插入其他命令，所以原子；但脚本执行时间过长会阻塞所有请求，复杂脚本要控制规模，避免 `KEYS`/大循环。
- Pipeline 只是把多条命令批量发、批量收，减少 RTT；命令之间仍可能插入其他客户端命令，不保证原子。事务 `MULTI/EXEC` 把命令排队后一起执行，但运行时错误（比如对 String 执行 `LPUSH`）不会回滚其他命令，Redis 事务没有回滚。
- `WATCH key` 在 `MULTI` 前监视 key，`EXEC` 时如果 key 被改过就放弃事务；这是乐观锁，适合低冲突场景。
- Lua 用 `KEYS`/`ARGV` 传参，返回 table 会被转成数组；集群模式下脚本访问的 key 必须同一个槽，用 hash tag 绑定。
- 需要「比较并设置」的原子操作优先用 Lua，不要用「GET 再 SET」两条命令；但 Lua 不是万能的，长脚本会拖住单线程。

## 8. Key 设计与运维

**一句话**：key 要可读、可定位、带业务维度；监控命中率、内存、慢查询、连接数、淘汰数和复制延迟。

要能回答：

- key 命名怎么设计？要不要带租户/环境前缀？
- 如何批量删除一类 key？`KEYS` 为什么不能在生产用？
- `SCAN` 的游标怎么用？有什么保证？
- 缓存命中率低怎么排查？
- 慢查询日志怎么开？`SLOWLOG GET` 怎么看？
- 连接数打满怎么办？客户端池怎么配？
- Redis 内存告警怎么处理？

**笔记**：

- 命名用 `业务:环境:租户:类型:id`，例如 `wms:prod:t1:user:42`；带环境/租户前缀便于隔离、排查和批量清理，但别让 key 太长（内存和网络都算成本）。项目里缓存 key 用 `company:code` 带租户，见 [[Redis]]。
- `KEYS pattern` 会遍历全库并阻塞单线程，生产禁用；用 `SCAN cursor MATCH pattern COUNT n` 渐进遍历。SCAN 保证「从开始到结束一直在的 key 至少返回一次」，可能重复、不保证快照一致，删除时要幂等。
- 命中率低：看 `INFO stats` 的 `keyspace_hits/misses`；常见原因是 TTL 太短、key 设计太分散、缓存穿透、写入后没回填、热点数据被淘汰。先定位是「没缓存」还是「缓存了但没命中」。
- 慢查询：`SLOWLOG GET N` 看执行时间、命令、参数；`slowlog-log-slower-than` 设阈值（比如 10ms），注意慢查询只记执行时间，不含网络/排队。大 key、`KEYS`、复杂 Lua、`SORT` 是常见来源。
- 连接数打满：看 `INFO clients` 的 `connected_clients`、`blocked_clients`；客户端池要设上限和超时，避免应用侧无限建连；Redis `maxclients` 到了会拒绝新连接。
- 内存告警：看 `INFO memory` 的 `used_memory`、`used_memory_rss`、`mem_fragmentation_ratio`、`evicted_keys`；先判断是「真用满」还是「碎片/复制缓冲区/客户端缓冲区」；扩容、淘汰策略、拆分实例、大 key 治理按原因选。

## 常见对比题

- Redis vs Memcached
- String vs Hash
- RDB vs AOF
- 主从 vs 哨兵 vs Cluster
- 缓存穿透 vs 击穿 vs 雪崩
- Lua vs Pipeline vs 事务
- `KEYS` vs `SCAN`

## 我现在到哪

| 块 | 现状 | 依据 |
| --- | --- | --- |
| 共享缓存、TTL、降级 | 项目里落地过 | [[Redis]]、[[异步导出落地]] |
| 登录态 keyVer、单端登录 | 项目里落地过 | [[登录态与踢线]]、[[keyVer踢线校验]] |
| Redisson 锁/信号量 | 项目里落地过 | [[Redisson]]、[[导出背压]] |
| 持久化、主从、哨兵、Cluster | 学习和面试准备，未在项目落地 | 本页 |
| Lua 脚本、big key/hot key 专项 | 未在项目落地 | 本页 |

## 边界

- 本页是索引，不是教材：每个问题只留一行，展开写到独立笔记。
- 项目里以缓存、锁、信号量为主，没有持久化和集群运维实战。
- 没有写过 Lua，也没有做过缓存击穿/雪崩的专项演练。
