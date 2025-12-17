# ChiloDBFuzz
（目前正在开发中！非本项目开发人员请勿使用，当前阶段使用出现的一切后果自负...）
    
（dev-ing）
## 简体中文
基于LLM与掩码变异生成测试用例的DBMS模糊测试工具。

## 如何使用

### docker镜像准备
ChiloDBFuzz的镜像需要从dockerfile构建，下面是具体的构建命令。（首先您要确定本机的docker已经被正确安装）

根据被测对象不同，构建命令略有区别，请根据被测对象进行选择。

我们默认的各DBMS版本选择，基本同SQUIRREL论文

参考文献：Squirrel: Testing Database Management Systems with Language Validity and Coverage Feedback

- SQLite：3.30.1
- MySQL：8.0.0
- MariaDB：10.5.3

对于PostgreSQL SQUIRREL中没有注明使用的DBMS版本，我们选择的版本为SQLRight论文中的相同版本

参考文献：Detecting Logical Bugs of DBMS with Coverage-based Guidance

- PostgreSQL:14.0

对于SQUIRREL和SQLRight都不原生支持的DBMS，我们选择最新的版本

- DuckDB：...

---
SQLite：

如果想要运行CHILO/SQUIRREL
```bash
cd {repo_path}
cd ./docker/sqlite
docker build -t chilodbfuzz:sqlite .
```

如果想要运行CLCC
```bash
cd {repo_path}
cd ./docker/sqlite
docker build -t clccdbfuzz:sqlite -f clcc_dockerfile .
```
---

MySQL:
```bash
cd {repo_path}
cd ./docker/mysql
docker build -t chilodbfuzz:sqlite .
```

---

### 容器启动和测试启动

SQLite (SQUIRREL/CHILO):
```bash
#下面语句请在主机终端1运行
docker run -it --cpuset-cpus="0,1" --privileged -p 5173:5173 --name sqlite_chilofuzz_test chilodbfuzz:sqlite /bin/bash

# 请首先编写config.yaml以及fuzz_config.yaml
vim ./config.yaml
echo core | sudo tee /proc/sys/kernel/core_pattern
# 设置 ulimit 以避免 AddressSanitizer 内存分配错误
ulimit -c unlimited
ulimit -v unlimited 

#下面请在主机终端2运行
docker exec -it sqlite_chilofuzz_test bash
cd ../ChiloDisco/ && python3 app.py  #启动ChiloDisco后端

#下面请在主机终端3运行
docker exec -it sqlite_chilofuzz_test bash
cd ../ChiloDisco/frontend/ && npm run dev -- --host 0.0.0.0 --port 5173

#下面请在主机终端1运行
python3 start_fuzz.py
```

SQLite (CLCC):
```bash
#下面请在终端1运行
docker run -it --privileged --cpuset-cpus="0,1" --name sqlite_clcc_test clccdbfuzz:sqlite /bin/bash

#下面请在终端2运行
docker exec -it sqlite_clcc_test bash

```

