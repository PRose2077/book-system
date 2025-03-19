import os
import hanlp
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_hanlp_model():
    """预下载HanLP模型到本地"""
    try:
        logger.info("开始下载HanLP模型...")
        # 加载模型会自动下载
        model = hanlp.load(hanlp.pretrained.mtl.CLOSE_TOK_POS_NER_SRL_DEP_SDP_CON_ELECTRA_SMALL_ZH)
        logger.info(f"HanLP模型下载成功，保存在: {os.path.expanduser('~/.hanlp')}")
        return True
    except Exception as e:
        logger.error(f"下载HanLP模型失败: {str(e)}")
        return False

if __name__ == "__main__":
    download_hanlp_model() 