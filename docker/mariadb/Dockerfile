FROM ubuntu:22.04
LABEL maintainer="ZRCL"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get -y install \
    make cmake build-essential gdb sudo git \
    tcl8.6 tcl8.6-tdbc-sqlite3 bison\
    clang-15 llvm-15 lld ninja-build pkg-config \
    libpq-dev libyaml-cpp-dev wget bzip2 ca-certificates \
    python3 python3-pip python3-dev vim curl gnupg libmysqlclient-dev libtirpc-dev rpcsvc-proto \
    apt-transport-https software-properties-common gnutls-dev\
    && python3 -m pip install --upgrade pip \
    && python3 -m pip install --no-cache-dir --break-system-packages --ignore-installed\
        Flask==3.0.3 \
        gunicorn==22.0.0 \
        annotated-types==0.7.0 \
        anyio==4.11.0 \
        certifi==2025.10.5 \
        colorama==0.4.6 \
        distro==1.9.0 \
        h11==0.16.0 \
        httpcore==1.0.9 \
        httpx==0.28.1 \
        idna==3.11 \
        jiter==0.11.0 \
        openai==2.3.0 \
        pydantic==2.12.1 \
        pydantic-core==2.41.3 \
        pyyaml==6.0.3 \
        sniffio==1.3.1 \
        tqdm==4.67.1 \
        typing-extensions==4.15.0 \
        typing-inspection==0.4.2 \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home && \
    groupadd chilo && \
    useradd -l -K UMASK=0000 -d /home -g chilo chilo && \
    chown chilo:chilo /home

RUN	echo "chilo:chilo" | chpasswd && usermod -a -G sudo chilo
RUN chmod +w /etc/sudoers && \
    echo "%chilo   ALL=(ALL:ALL)NOPASSWD:ALL" >> /etc/sudoers && \
    chmod -w /etc/sudoers

USER chilo
WORKDIR /home
RUN mkdir ./crashes

#用于打断cache！
ADD ./temp /tmp/tempfile

# 克隆或更新 ChiloDBFuzz 仓库
RUN git clone https://github.com/zrclzrcl/ChiloDBFuzz.git

#搞定AFL++
RUN cd /home/ChiloDBFuzz && git submodule update --init && \
    cd AFLplusplus && LLVM_CONFIG=llvm-config-15 make -j$(nproc)

#搞定SQUIRREL的MySQL WARPPER
RUN git clone https://github.com/Dobigthing666/Squirrel.git && \
    cd Squirrel && git submodule update --init && \
    cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -Wno-dev -DMYSQL=ON && cmake --build build -j

# 构建mariadb
RUN git clone --depth=1 --branch mariadb-10.5.3 https://github.com/MariaDB/server.git mariadb && \
    mkdir bld && cd bld/

WORKDIR /home/bld
RUN sudo apt-get update && sudo apt-get install -y bison flex libncurses5-dev \
libssl-dev zlib1g-dev libgnutls28-dev zlib1g-dev libpcre3-dev libevent-dev libpcre2-dev 

# ===== OpenSSL 1.1 (必须用 root 安装到 /opt 并写入 ld.so) =====
USER root
ARG OPENSSL_11_VER=1.1.1w
RUN apt-get update && apt-get install -y --no-install-recommends \
      perl make gcc g++ wget ca-certificates zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    cd /tmp; \
    wget -O openssl-${OPENSSL_11_VER}.tar.gz https://www.openssl.org/source/openssl-${OPENSSL_11_VER}.tar.gz; \
    tar xf openssl-${OPENSSL_11_VER}.tar.gz; \
    cd openssl-${OPENSSL_11_VER}; \
    ./config --prefix=/opt/openssl-1.1 --openssldir=/opt/openssl-1.1 shared zlib; \
    make -j"$(nproc)"; \
    make install_sw; \
    echo "/opt/openssl-1.1/lib" > /etc/ld.so.conf.d/openssl-1.1.conf; \
    ldconfig; \
    /opt/openssl-1.1/bin/openssl version; \
    rm -rf /tmp/openssl-*

USER chilo

ENV CC=/home/ChiloDBFuzz/AFLplusplus/afl-clang-fast
ENV CXX=/home/ChiloDBFuzz/AFLplusplus/afl-clang-fast++

# 第一次执行 cmake，允许它失败（目的是为了让它把 libmariadb 的文件下载/生成出来）
RUN (AFL_USE_ASAN=1 \
    CC=/home/ChiloDBFuzz/AFLplusplus/afl-clang-fast \
    CXX=/home/ChiloDBFuzz/AFLplusplus/afl-clang-fast++ \
    cmake ../mariadb -DCMAKE_BUILD_TYPE=Debug -DCMAKE_REQUIRED_LIBRARIES=m) || true

# 此时文件一定已经存在了，执行修复
RUN sed -i 's/END()/ENDIF()/g' ../mariadb/libmariadb/cmake/ConnectorName.cmake
RUN rm -f CMakeCache.txt && rm -rf CMakeFiles
# 第二次执行 cmake，这次它会读取修复后的文件，顺利通过

RUN AFL_USE_ASAN=1 \
    CC=/home/ChiloDBFuzz/AFLplusplus/afl-clang-fast \
    CXX=/home/ChiloDBFuzz/AFLplusplus/afl-clang-fast++ \
    cmake ../mariadb -DCMAKE_BUILD_TYPE=Debug -DCMAKE_REQUIRED_LIBRARIES=m \
    -DENABLE_ASAN=ON \
    -DCMAKE_C_FLAGS="-Wno-error" \
    -DCMAKE_CXX_FLAGS="-Wno-error" \
    -DERR_IGNORE_WERROR=ON \
    -DWITH_SSL=/opt/openssl-1.1 \
    -DOPENSSL_ROOT_DIR=/opt/openssl-1.1 \
    -DOPENSSL_INCLUDE_DIR=/opt/openssl-1.1/include \
    -DOPENSSL_SSL_LIBRARY=/opt/openssl-1.1/lib/libssl.so \
    -DOPENSSL_CRYPTO_LIBRARY=/opt/openssl-1.1/lib/libcrypto.so \
    -DCMAKE_EXE_LINKER_FLAGS="-Wl,-rpath,/opt/openssl-1.1/lib" \
    -DCMAKE_SHARED_LINKER_FLAGS="-Wl,-rpath,/opt/openssl-1.1/lib"

RUN find . -name "flags.make" -exec sed -i 's/-Werror//g' {} +
# 用 AFL 编译器启用 ASAN
ENV AFL_USE_ASAN=1
RUN make 
RUN sudo cmake --install . --prefix /usr/local/mysql/

RUN ldd /usr/local/mysql/bin/mariadbd | egrep "libssl|libcrypto" || true
RUN /usr/local/mysql/bin/mariadbd --version || true

RUN sudo chown chilo:chilo /usr/local/mysql/ -R && \
    cd /usr/local/mysql/ && \
    LD_LIBRARY_PATH=/opt/openssl-1.1/lib:$LD_LIBRARY_PATH \
    scripts/mysql_install_db --user=chilo --auth-root-authentication-method=normal

#获得mapsize
RUN AFL_DEBUG=1 __AFL_SHM_ID=1234 /usr/local/mysql/bin/mariadbd 2>&1 | grep "__afl_map_size" | tail -n 1 | cut -d"," -f8 | cut -d" " -f 3 > /tmp/mapsize

#搞定disco
WORKDIR /home/ChiloDBFuzz/ChiloDisco/frontend
RUN npm ci && npm run build

WORKDIR /home/ChiloDBFuzz/code
