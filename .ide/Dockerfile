FROM cnbcool/default-dev-env:latest

ENV LANG C.UTF-8
RUN apt-get update && apt-get install -y wget unzip openssh-server
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    uv python install 3.14.2
    
    