FROM python:3.8-slim

RUN apt-get update \
  && apt-get -y install --reinstall \
  build-essential python3-dev libopenblas-dev \
  git wget \
  redis-server \
  && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
RUN pip install qiskit matplotlib
RUN pip install $(pip freeze 2>/dev/null| grep aqua | sed -e 's/==/[torch,pyscf]==/')
RUN pip install https://github.com/rpmuller/pyquante2/archive/master.zip
RUN pip install cvxopt

RUN mkdir /qiskit-runtime
RUN mkdir /qiskit-runtime/logs

WORKDIR /qiskit-runtime

COPY ./requirements.txt .
RUN pip install -r requirements.txt

COPY ./requirements-server.txt .
RUN pip install -r requirements-server.txt

EXPOSE 8000
COPY ./scripts/start-test-server.sh .
CMD NUM_WORKERS=2 bash start-test-server.sh