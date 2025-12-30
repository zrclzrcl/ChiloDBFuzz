FROM ubuntu:22.04
LABEL maintainer="ZRCL"

ENV DEBIAN_FRONTEND noninteractive

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
#先搞定squirrel的第三方库 absl
RUN git clone https://github.com/abseil/abseil-cpp.git && cd abseil-cpp && mkdir build && cd build && \
    cmake -DCMAKE_CXX_STANDARD=17 \
          -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
          -DABSL_BUILD_TESTING=OFF \
          -DBUILD_SHARED_LIBS=ON \
          .. && \
    make -j$(nproc) && \
    sudo make install && \
    sudo ldconfig

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


RUN sudo apt-get -y install apt-transport-https curl software-properties-common gnutls-dev

# 构建mysql
RUN git clone --branch mysql-8.0.2 --depth 1 https://github.com/mysql/mysql-server.git mysql

RUN mkdir bld

WORKDIR /home/bld

# 用 AFL 编译器启用 ASAN
ENV CC=/home/ChiloDBFuzz/AFLplusplus/afl-clang-fast
ENV CXX=/home/ChiloDBFuzz/AFLplusplus/afl-clang-fast++
ENV AFL_USE_ASAN=1

# ----------------- 源码修复补丁集 (START) -----------------

# 补丁 2: 修复 rpl_transaction_write_set_ctx.h 缺少 <string> 头文件的问题 (现在遇到的)
# 使用 sed 在文件第一行插入 #include <string>
RUN sed -i '1i #include <string>' /home/mysql/sql/rpl_transaction_write_set_ctx.h

# ----------------- 源码修复补丁集 (END) -------------------

RUN cmake ../mysql/ -DDOWNLOAD_BOOST=1 -DWITH_BOOST=../boost \
    -DWITH_DEBUG=1 -DCPACK_MONOLITHIC_INSTALL=1 -DWITH_UNIT_TESTS=OFF \
    -DCMAKE_C_FLAGS="-I/usr/include/tirpc" \
    -DCMAKE_CXX_FLAGS="-I/usr/include/tirpc" \
    -DCMAKE_EXE_LINKER_FLAGS="-ltirpc"\
    -DCMAKE_CXX_STANDARD=14 \
    -DCMAKE_BUILD_TYPE=Debug

RUN make && sudo cmake --install . --prefix /usr/local/mysql/

RUN sudo chown chilo:chilo /usr/local/mysql/ -R && \
    cd /usr/local/mysql/ && mkdir mysql-files && chmod 750 mysql-files && \
    AFL_IGNORE_PROBLEMS=1 bin/mysqld --initialize-insecure --user=chilo && bin/mysql_ssl_rsa_setup

#获得mapsize
RUN AFL_DEBUG=1 __AFL_SHM_ID=1234 /usr/local/mysql/bin/mysqld 2>&1 | grep "__afl_map_size" | tail -n 1 | cut -d"," -f8 | cut -d" " -f 3 > /tmp/mapsize

#搞定disco
WORKDIR /home/ChiloDBFuzz/ChiloDisco/frontend
RUN npm ci && npm run build

WORKDIR /home/ChiloDBFuzz/code
