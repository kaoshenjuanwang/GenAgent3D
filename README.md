# GenAgent3D
一个基于LLM的视觉生成智能体


# WGAN-GP Image Generation Project

## Environment Setup

### System Requirements
- Python 3.8 or higher
- CUDA-capable GPU (recommended) or CPU
- At least 8GB RAM (16GB recommended)
- Sufficient disk space for dataset and model checkpoints

### Installation Steps

1. **Create a virtual environment (recommended)**
   ```bash
   # Using conda
   conda create -n wgan-gp python=3.8
   conda activate wgan-gp

   # Or using venv
   python -m venv wgan-gp-env
   # On Windows
   .\wgan-gp-env\Scripts\activate
   # On Linux/Mac
   source wgan-gp-env/bin/activate
   ```

2. **Install PyTorch**
   - For CUDA (GPU) support:
     ```bash
     # For CUDA 11.8
     pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu118
     ```
   - For CPU only:
     ```bash
     pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cpu
     ```

3. **Install other dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Dataset Preparation
- Place your image dataset in the specified directory (default: `E:\study\programming\schoolwork\shenduxuexishiyan\data`)
- Images should be organized in a folder structure compatible with `torchvision.datasets.ImageFolder`
- Supported image formats: JPG, PNG, etc.

## Running the Code

1. **Configuration**
   - Open `1.py` and modify the following parameters as needed:
     - `DATA_PATH`: Path to your dataset
     - `OUTPUT_DIR`: Directory for saving results
     - `IMG_SIZE`: Image size (default: 96)
     - `BATCH_SIZE`: Batch size (adjust based on GPU memory)
     - `NUM_EPOCHS`: Number of training epochs
     - `LOAD_MODEL`: Set to `False` for fresh training

2. **Training**
   ```bash
   python 1.py
   ```

3. **Monitoring**
   - Training progress will be displayed with progress bars
   - Generated images will be saved in the `OUTPUT_DIR`
   - Checkpoint files will be saved periodically

## Output Files
- Generated images: `epoch_*.png`
- Model checkpoints: `checkpoint.pth`, `checkpoint_epoch_*.pth`
- Final models: `generator_final.pth`, `discriminator_final.pth`
- Evaluation results: `final_generation_grid.png`

## Troubleshooting

### Common Issues
1. **CUDA out of memory**
   - Reduce `BATCH_SIZE`
   - Use smaller image size
   - Close other GPU applications

2. **Slow training**
   - Ensure CUDA is properly installed
   - Check GPU utilization
   - Consider using a more powerful GPU

3. **Poor generation quality**
   - Increase `NUM_EPOCHS`
   - Adjust learning rate
   - Check dataset quality and size

### Getting Help
If you encounter any issues:
1. Check the error message carefully
2. Ensure all dependencies are correctly installed
3. Verify CUDA installation if using GPU
4. Check dataset path and format

## License
This project is for educational purposes only. 
