import copy
import logging
import sys
import time
import asyncio
# from Tools.demo.spreadsheet import translate

from .Utils import SymbolWidthUtil, RawData, Pbar, set_proxy
from .config import config
from .TranslateApi import TranslatorsApi
# 设置代理后导入翻译模块
try:
    set_proxy(config.proxy)

except Exception as exception:
    if type(exception).__name__ == "TranslatorError":
        logging.error(f"Translation engine initialization failed: {exception}")
    else:
        logging.error(f"Error occurred when setting proxy: {exception}")
    sys.exit(1)

MAX_RETRY = 5


class TranslateError(Exception):
    pass


class Translator:
    _translator = TranslatorsApi()
    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent  # 设置最大并行数

        self.translators = Translator._translator.create_translator(config.translator)

    async def translate(self, source_text: str, src_lang: str, target_lang: str, retries: int = 0) -> str:
        logging.debug(f"Translating {src_lang} to {target_lang}, length={len(source_text)}, retries={retries}")
        if retries >= MAX_RETRY:
            raise TranslateError(f"Translate failed after {MAX_RETRY} retries.")
        try:
            # print(source_text)
            result = await self.translators.translate_async(
                text=str(source_text),
                from_lang=src_lang,
                to_lang=target_lang,
            )
            if result is None:
                retries += 1
                logging.warning(f"Translate failed, retry {retries}/{MAX_RETRY}")
                await asyncio.sleep(5)
                return await self.translate(source_text, src_lang, target_lang, retries)
            return result
        except Exception as e:
            retries += 1
            logging.error(f"Translate error: {e}, retry {retries}/{MAX_RETRY}")
            # 重试时等待时间递增
            await asyncio.sleep(0.2 * pow(2, retries))
            return await self.translate(source_text, src_lang, target_lang, retries)

    async def __translate_with_skipped_chars(self, chunk: tuple[dict[int, str], dict[int, str], int], src_lang: str,
                                       target_lang: str, pbar: Pbar) -> str:
        """
        翻译时忽略在config.py中配置的正则表达式，翻译后保证格式不变
        :param chunk: 本次翻译的文本块
        :return: 翻译后的文本
        """
        # 跳过的部分和需要翻译的部分以及所有部分的数量
        skipped_parts, need_translate_parts, parts_count = chunk

        text_to_translate = "\n".join(need_translate_parts.values())
        # 确保api接口返回了结果
        while (translated_text := await self.translate(text_to_translate, src_lang, target_lang)) is None:
            pass

        pbar.update(len(text_to_translate))
        translated_text = [line.strip(" ") for line in translated_text.splitlines()]
        # 更新翻译部分的内容
        for position, key in enumerate(need_translate_parts.keys()):
            need_translate_parts[key] = translated_text[position]
        #
        # if not target_lang.lower().startswith("zh"):
        #     # 如果是不是中文，则将skipped_parts中的全角符号变为半角符号
        need_translate_parts = {key: SymbolWidthUtil.full_to_half(value) for key, value in need_translate_parts.items()}

        total_parts = {**skipped_parts, **need_translate_parts}
        return "".join(total_parts[i] for i in range(parts_count))

    # async def translate_in_batch(self, raw_data: RawData, src_lang: str, target_lang: str, pbar: Pbar) -> str:
    #     """
    #     分批次翻译
    #     """
    #     translated_text = [await self.__translate_with_skipped_chars(chunk, src_lang, target_lang, pbar) for chunk in
    #                        # 深拷贝，避免修改原始数据
    #                        copy.deepcopy(raw_data.chunks)]
    #     lines = ''.join(translated_text).splitlines()
    #     # 将空行插入回去
    #     for i in raw_data.empty_line_position:
    #         lines.insert(i, '')
    #     return '\n'.join(lines) + '\n'

    async def limited_translate(self,semaphore, chunk, src_lang, target_lang, pbar):
        async with semaphore:
            return await self.__translate_with_skipped_chars(chunk, src_lang, target_lang, pbar)

    async def translate_in_batch(self, raw_data: RawData, src_lang: str, target_lang: str, pbar: Pbar) -> str:
        """
        分批次翻译 (Batch Translation)
        """
        # Deep copy to avoid modifying the original data
        chunks_copy = copy.deepcopy(raw_data.chunks)

        # Await each translation coroutine properly within the list comprehension
        # translated_texts = [
        #     await self.__translate_with_skipped_chars(chunk, src_lang, target_lang, pbar)
        #     for chunk in chunks_copy
        # ]

        semaphore = asyncio.Semaphore(self.max_concurrent)  # 设置最大并行数
        tasks = [
            self.limited_translate(semaphore, chunk, src_lang, target_lang, pbar)
            for chunk in chunks_copy
        ]
        translated_texts = await asyncio.gather(*tasks)

        # Concatenate all translated chunks into a single string and split into lines
        concatenated_text = ''.join(translated_texts)
        lines = concatenated_text.splitlines()

        # Insert empty lines back at their original positions
        for position in raw_data.empty_line_position:
            lines.insert(position, '')

        # Join all lines back into a single string with newline characters
        return '\n'.join(lines) + '\n'
async def main():
    translator = Translator()
    text = """
          Lax pairs informed neural networks solving integrable systems  
    """
    targetText =await translator.translate(text, src_lang='en', target_lang='zh')
    print("==============================")
    print(targetText)
if __name__ == '__main__':
    asyncio.run(main())