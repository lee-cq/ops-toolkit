FROM cnbcool/default-dev-env:latest

ENV LANG C.UTF-8
RUN apt-get update && apt-get install -y wget unzip openssh-server
RUN mkdir -p /ide_cnb \
    && wget https://download.jetbrains.com/python/pycharm-2025.2.1.1.tar.gz \
    && tar -xzf pycharm-2025.2.1.1.tar.gz -C /ide_cnb 

RUN curl -LsSf https://astral.sh/uv/install.sh | sh