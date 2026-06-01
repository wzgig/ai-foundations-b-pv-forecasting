# import subprocess
# import sys
# import platform
# import tensorflow as tf
#
#
# def get_cuda_version():
#     """检查系统CUDA版本"""
#     try:
#         nvcc_output = subprocess.check_output(["nvcc", "--version"], stderr=subprocess.STDOUT).decode()
#         for line in nvcc_output.split('\n'):
#             if "release" in line:
#                 release_idx = line.find("release") + 8
#                 release_version = line[release_idx:].split(',')[0].strip()
#                 return release_version
#         return None
#     except (subprocess.CalledProcessError, FileNotFoundError):
#         return None
#
#
# def install_tensorflow():
#     """根据环境安装TensorFlow"""
#     print("开始安装TensorFlow和Keras...")
#
#     # 检查CUDA版本
#     cuda_version = get_cuda_version()
#
#     # 确定Python版本
#     python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
#
#     # 根据操作系统和CUDA支持选择安装命令
#     if cuda_version:
#         print(f"检测到CUDA版本: {cuda_version}，将安装GPU版本")
#         command = [
#             sys.executable, "-m", "pip", "install",
#             "tensorflow-gpu",
#             "--extra-index-url", "https://download.pytorch.org/whl/cu" + cuda_version.replace('.', '')
#         ]
#     else:
#         print("未检测到CUDA，将安装CPU版本")
#         command = [
#             sys.executable, "-m", "pip", "install",
#             "tensorflow"
#         ]
#
#     # 执行安装命令
#     print(f"执行命令: {' '.join(command)}")
#     try:
#         subprocess.run(command, check=True)
#         print("TensorFlow安装成功！")
#
#         # 验证安装
#         try:
#             import tensorflow as tf
#             print(f"安装版本: {tf.__version__}")
#             print(f"Keras版本: {tf.keras.__version__}")
#             if tf.test.is_gpu_available():
#                 print("GPU支持已启用")
#             else:
#                 print("已安装CPU版本")
#         except Exception as e:
#             print(f"验证失败: {e}")
#
#     except subprocess.CalledProcessError as e:
#         print(f"安装失败: {e}")
#         print("请尝试手动安装:")
#         print("  1. 打开命令行工具")
#         print("  2. 执行: pip install tensorflow")
#         print("  3. 若需要GPU支持: pip install tensorflow-gpu")
#
#
# if __name__ == "__main__":
#     print(f"Python环境: {platform.python_version()}")
#     install_tensorflow()
# import subprocess
# import sys
#
# def install_statsmodels():
#     """安装statsmodels库"""
#     try:
#         # 执行pip安装命令
#         subprocess.run(
#             [sys.executable, "-m", "pip", "install", "statsmodels"],
#             check=True,  # 安装失败时抛出异常
#             stdout=subprocess.PIPE,  # 捕获输出信息
#             stderr=subprocess.PIPE
#         )
#         print("statsmodels库安装成功！")
#     except subprocess.CalledProcessError as e:
#         print(f"安装失败，错误信息：\n{e.stderr.decode('utf-8')}")
#     except Exception as e:
#         print(f"发生未知错误：{e}")
#
# if __name__ == "__main__":
#     install_statsmodels()
import subprocess
import sys

def install_shap():
    """安装Optuna库"""
    try:
        # 执行pip安装命令
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "shap"],
            check=True,  # 安装失败时抛出异常
            stdout=subprocess.PIPE,  # 捕获输出信息
            stderr=subprocess.PIPE
        )
        print("shap库安装成功！")
    except subprocess.CalledProcessError as e:
        print(f"安装失败，错误信息：\n{e.stderr.decode('utf-8')}")
    except Exception as e:
        print(f"发生未知错误：{e}")

if __name__ == "__main__":
    install_shap()