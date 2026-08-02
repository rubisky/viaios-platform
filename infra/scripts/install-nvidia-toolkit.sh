#!/bin/bash
# Install NVIDIA Container Toolkit for GPU-accelerated Docker (Triton GPU mode)
set -e

echo "Installing NVIDIA Container Toolkit..."

# Add NVIDIA repo
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install
apt-get update && apt-get install -y nvidia-container-toolkit

# Configure Docker
nvidia-ctk runtime configure --runtime=docker
systemctl restart docker

echo "Done! Restart Triton with GPU:"
echo "  docker rm -f viaios-triton"
echo "  docker run -d --gpus all --name viaios-triton -p 8000:8000 -p 8001:8001 -p 8002:8002 \\"
echo "    -v /opt/viaios/models/triton:/models nvcr.io/nvidia/tritonserver:24.01-py3 \\"
echo "    tritonserver --model-repository=/models"
