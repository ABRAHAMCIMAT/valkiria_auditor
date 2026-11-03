# Image for one AgentCore runtime. Build from backend/agentcore so shared/ is in
# the context, selecting the agent with: --build-arg AGENT_DIR=planning_agent
FROM public.ecr.aws/docker/library/python:3.12-slim

ARG AGENT_DIR
ENV AGENT_DIR=${AGENT_DIR} PYTHONUNBUFFERED=1 DOCKER_CONTAINER=1

WORKDIR /app
COPY ${AGENT_DIR}/requirements.lock ./requirements.lock
RUN pip install --no-cache-dir --only-binary :all: --require-hashes -r requirements.lock

# src/main.py adds ../.. to sys.path, so shared/ must sit two levels above it
COPY shared ./shared
COPY ${AGENT_DIR}/src ./${AGENT_DIR}/src

RUN useradd --create-home --uid 1000 agent
USER agent

EXPOSE 8080
CMD ["sh", "-c", "exec python ${AGENT_DIR}/src/main.py"]
