FROM ubuntu:22.04
LABEL maintainer="ZRCL"

ENV DEBIAN_FRONTEND noninteractive

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
ADD ./temp /tmp/temp

# 克隆或更新 ChiloDBFuzz
RUN git clone https://github.com/zrclzrcl/ChiloDBFuzz.git

#搞定AFL++
RUN cd /home/ChiloDBFuzz && git submodule update --init && \
    cd AFLplusplus && LLVM_CONFIG=llvm-config-15 make -j$(nproc)

RUN git clone --branch v0.7.1 --depth 1 https://github.com/duckdb/duckdb.git duckdb && cd duckdb && mkdir bld

WORKDIR /home/duckdb

ENV CC=/home/ChiloDBFuzz/AFLplusplus/afl-clang-fast
ENV CXX=/home/ChiloDBFuzz/AFLplusplus/afl-clang-fast++
ENV AFL_USE_ASAN=1
ENV CFLAGS="-O0 -g"
ENV CXXFLAGS="-O0 -g"
RUN make relassert -j$(nproc)

RUN AFL_DEBUG=1 /home/duckdb/build/release/duckdb -f 1 2>&1 | grep "__afl_map_size" | tail -n 1 | cut -d"," -f8 | cut -d" " -f 3 > /tmp/mapsize

#搞定disco
WORKDIR /home/ChiloDBFuzz/ChiloDisco/frontend
RUN npm ci && npm run build

WORKDIR /home/ChiloDBFuzz/code