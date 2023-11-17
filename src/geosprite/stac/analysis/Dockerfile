FROM public.ecr.aws/lambda/python:3.10

ENV PACKAGE=/var/task

# Copy local files
COPY lambda_function.py $PACKAGE/lambda_function.py

# install package
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -t ${PACKAGE} rasterio shapely

# Create package.zip
RUN yum install zip -y
RUN cd $PACKAGE && zip -r9q /tmp/package.zip *

# docker build --tag package:latest .
# docker run --name package -w /var/task -itd package:latest bash
# docker cp package:/tmp/package.zip package.zip
# docker stop package
# docker rm package
