FROM ubuntu:22.04
LABEL maintainer="ZRCL"

ENV DEBIAN_FRONTEND noninteractive

RUN sed -i 's|archive.ubuntu.com|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list && \
    sed -i 's|security.ubuntu.com|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list

RUN apt-get update && apt-get -y install \
    make cmake build-essential gdb sudo git \
    tcl8.6 tcl8.6-tdbc-sqlite3 \
    clang-15 llvm-15 lld ninja-build pkg-config \
    libpq-dev libyaml-cpp-dev wget bzip2 ca-certificates \
    python3 python3-pip python3-dev vim curl gnupg\
    && python3 -m pip install --upgrade pip \
    && python3 -m pip install --no-cache-dir \
        numpy \
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

#搞定SQUIRREL的PostgreSQL WARPPER
RUN git clone https://github.com/s3team/Squirrel.git && \
    cd Squirrel && git submodule update --init && \
    cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -Wno-dev -DPOSTGRESQL=ON && cmake --build build -j

#用于打断cache！
ADD ./temp /tmp/temp
# 克隆或更新 ChiloDBFuzz 仓库（强制使用 CACHEBUST）
RUN git clone https://github.com/zrclzrcl/ChiloDBFuzz.git

#搞定AFL++
RUN cd /home/ChiloDBFuzz && git submodule update --init && \
    cd AFLplusplus && LLVM_CONFIG=llvm-config-15 make -j$(nproc)

# 构建postgres
RUN git clone --depth=1 --branch REL_14_0 https://github.com/postgres/postgres.git postgres/ && mkdir bld/
WORKDIR /home/postgres/bld

RUN sudo apt-get update && sudo apt-get install -y \
    libreadline-dev bison \
    flex

ENV AFL_USE_ASAN=1
ENV CC=/home/ChiloDBFuzz/AFLplusplus/afl-clang-fast
ENV CXX=/home/ChiloDBFuzz/AFLplusplus/afl-clang-fast++
RUN ../configure \
    --enable-debug \
    --enable-cassert \
    CFLAGS="-O1 -g" \
    CXXFLAGS="-O1 -g"

RUN  make -j && sudo make install && \
    sudo mkdir /usr/local/pgsql/data && sudo chown chilo /usr/local/pgsql/data &&  \
    ASAN_OPTIONS=detect_leaks=0 AFL_IGNORE_PROBLEMS=1 /usr/local/pgsql/bin/initdb -D /usr/local/pgsql/data

RUN AFL_DEBUG=1 __AFL_SHM_ID=1234 /usr/local/pgsql/bin/postgres 2>&1 | grep "__afl_map_size" | tail -n 1 | cut -d"," -f8 | cut -d" " -f 3 > /tmp/mapsize

#搞定disco
WORKDIR /home/ChiloDBFuzz/ChiloDisco/frontend
RUN npm ci && npm run build

WORKDIR /home/ChiloDBFuzz/code