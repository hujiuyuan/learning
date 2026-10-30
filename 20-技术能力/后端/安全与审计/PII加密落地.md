---
type: 实践
技能点: PII加密
项目: [muou]
时间: 2026-09
证据: 实战
---

# PII加密落地

技能点：[[PII加密]] · 项目：muou · 2026-09

场景：[[加密与查重]]

## 我想干什么

证件号（HKID、护照号）不能明文落库，但跨租户去重必须能按证件号精确命中；列表和详情只给掩码；日志、审计、错误详情里不能出现明文。

## 我干了什么

- **加密**：`PiiCipher` 用 AES-256-GCM，12 字节随机 IV、128 位 tag、32 字节 DEK，密文 `[IV][密文][TAG]`；每次加密现取 IV（`PiiCipher.java:13-32,45-64`）。
- **信封**：每条记录现取 DEK，KEK 包裹后与密文一起存，版本串跟着走；解密先解包再解业务密文（`IdNoVault.java:18-29`）。
- **查重**：`PiiHasher` 做规范化 + HMAC-SHA256（类型码|国籍|号码），pepper 按版本取；指纹落独立列并建索引（`PiiHasher.java:33-96`、`V202609112100__core_init.sql:235-237,288`）。
- **展示**：掩码模板化，列表直接读掩码列，不解密（`PiiMasker.java:18,220-255`、DDL 注释 `:272`）。
- **审计**：敏感字段只落 `{mask, ref}`（`AuditEnvelopeBuilder.java:128-134`）。
- **启动体检**：每个 KeyProvider 查环境名、公开测试密钥指纹、包裹解包自检（`KeyProviderGuard.java:47-110`）。
- **测试**：IV 每次不同、篡改一字节必抛、错钥/错长度/短密文都有错误码（`PiiCipherTest.java:29-100`）。

## 犯了什么错 / 误判

下面几条是代码注释里明确记录过的坑与修法。

1. **把启动断言写在装配方法里**：`PiiCryptoConfig` 的装配方法带 `@ConditionalOnMissingBean`，服务自建 KeyProvider 时整段不跑，环境断言一条都不跑，仓库里的公开测试密钥照样能拿去加密真实证件号（`KeyProviderGuard.java:24-27` 记录了这个问题）。→ 改成 bean 后处理器 + 启动收尾，对容器里每个 KeyProvider 都查，懒加载的也拉出来查（`KeyProviderGuard.java:29,47-63`）。
2. **想过拿密文判重**：AEAD 每次随机 IV，同一人两次密文不同，判重判不了；掩码只剩头尾，会把不同的人判成同一个（DDL 注释 `V202609112100__core_init.sql:273`）。→ 单独做 HMAC 指纹列。
3. **想过版本对不上就用当前 KEK 再试一次**：那会把「密钥配错」掩盖成一次成功解密，数据看起来正常、其实用错了钥匙（`FileKeyProvider.java:86-90`）。→ 版本不符直接抛。
4. **想过列表页解密后再掩码**：每行一次解密，明文进应用内存；应落掩码列、展示直接取（DDL 注释 `:272`）。
5. **以为看文件名就能认出测试密钥**：密钥文件可以复制、改名，文件名挡不住；要认密钥指纹。预发/生产挂公开测试密钥时启动成功、加密照算、没有告警，等发现时一批数据已经用人人可读的密钥加过（`KeyProviderGuard.java:78-82`）。→ 认 SHA-256 指纹，显式 `muou.pii.allow-test-key=true` 才放行（`:83-95`）。

## 怎么解决

- 把保障收进唯一入口：加解密只在 `PiiCipher`，密钥只在 `KeyProvider`，查重只在 `PiiHasher`。
- 启动期失败优先：环境名、密钥指纹、自检、审计表列缺一律起不来。
- 用测试钉住安全性：随机 IV、篡改检测、错钥、错长度、短密文都有用例。

## 现在的规矩

- 加密列只存密文，查重只认指纹列，展示只认掩码列；三列同改。
- 密钥不落业务代码；DEK 用完清零（`IdNoVault.java:22,28`）；缺密钥不回落明文（`:15-16`）。
- 错版本不回退，预发/生产禁用公开测试密钥。
- 审计、日志、错误详情里不出现明文或密文。

## 证据

- 加解密：`muou-backend/muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/pii/crypto/PiiCipher.java:13-104`
- 启动体检：`muou-backend/muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/pii/KeyProviderGuard.java:29-110`
- 文件密钥：`muou-backend/muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/pii/crypto/FileKeyProvider.java:24-109`
- 查重哈希：`muou-backend/muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/pii/crypto/PiiHasher.java:16-96`
- 信封落地：`muou-backend/muou-server-member/muou-member-app/src/main/java/com/voidtech/muou/member/roster/service/IdNoVault.java:18-29`
- 指纹调用：`muou-backend/muou-server-member/muou-member-app/src/main/java/com/voidtech/muou/member/application/proxy/service/IdFingerprints.java:46-52`
- 表结构：`muou-backend/muou-app-ops/databases/migration/core/V202609112100__core_init.sql:235-237,271-273,288`
- 测试：`muou-backend/muou-common/muou-common-app/src/test/java/com/voidtech/muou/common/pii/crypto/PiiCipherTest.java:29-100`

设计输入：`muou_arch/adr/0009-pii-encryption.md`（作者 dodo），不作为个人实战证据。
