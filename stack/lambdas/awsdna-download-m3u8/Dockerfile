ARG FUNCTION_DIR="/function"

FROM public.ecr.aws/bitnami/python:3.8 as build-image

# Install aws-lambda-cpp build dependencies
RUN apt-get update && \
  apt-get install -y \
  g++ \
  make \
  cmake \
  unzip \
  libcurl4-openssl-dev

# Include global arg in this stage of the build
ARG FUNCTION_DIR
# Create function directory
RUN mkdir -p ${FUNCTION_DIR}

# Install the runtime interface client
RUN pip install \
  --target ${FUNCTION_DIR} \
  awslambdaric

# Multi-stage build: grab a fresh copy of the base image
FROM public.ecr.aws/bitnami/python:3.8
# Install the function's dependencies
# Copy file requirements.txt from your project folder and install
# the requirements in the app directory.
ARG FUNCTION_DIR
WORKDIR ${FUNCTION_DIR}
# Copy in the build image dependencies
COPY --from=build-image ${FUNCTION_DIR} ${FUNCTION_DIR}
# RUN yum update -y
# RUN yum install mesa-libGL-devel -y
# RUN yum install ffmpeg libavcodec-extra -y

RUN apt update -y
RUN apt install ffmpeg libavcodec-extra -y


RUN pip install --upgrade pip

COPY requirements.txt  .
RUN  pip install -r requirements.txt

# Copy helper functions
COPY video_processor.py video_processor.py

# Copy handler function (from the local app directory)
COPY  app.py  .

# Overwrite the command by providing a different command directly in the template.
ENTRYPOINT [ "/opt/bitnami/python/bin/python", "-m", "awslambdaric" ]
CMD ["app.lambda_function"]
