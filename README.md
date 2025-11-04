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


SQLite：
```bash
cd {repo_path}
cd ./docker/sqlite
docker build --build-arg CACHEBUST=$(date +%s) -t chilodbfuzz:sqlite .
```

### docker容器启动
```bash
#下面语句请在主机终端1运行
docker run -it --privileged -p 5173:5173 --name sqlite_chilofuzz_test chilodbfuzz:sqlite /bin/bash

# 请首先编写config.yaml以及fuzz_config.yaml
vim ./config.yaml
echo core | sudo tee /proc/sys/kernel/core_pattern

#下面请在主机终端2运行
docker exec -it sqlite_chilofuzz_test bash
cd ../ChiloDisco/ && python3 app.py  #启动ChiloDisco后端

#下面请在主机终端3运行
docker exec -it sqlite_chilofuzz_test bash
cd ../ChiloDisco/frontend/ && npm run dev -- --host 0.0.0.0

#下面请在主机终端1运行
python3 start_fuzz.py
```